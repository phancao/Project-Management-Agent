# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import asyncio
import base64
import json
import logging
import os
from typing import Annotated, Any, AsyncIterator, List, Optional, cast
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from langchain_core.messages import AIMessageChunk, BaseMessage, ToolMessage
from langgraph.checkpoint.mongodb import AsyncMongoDBSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command
from psycopg_pool import AsyncConnectionPool

from src.config.configuration import get_recursion_limit
from src.config.loader import get_bool_env, get_str_env
from src.config.report_style import ReportStyle
from src.config.tools import SELECTED_RAG_PROVIDER
from src.graph.builder import build_graph_with_memory
from src.graph.checkpoint import chat_stream_message
from src.graph.utils import (
    build_clarified_topic_from_history,
    reconstruct_clarification_history,
)
from src.llms.llm import get_configured_llm_models
from src.podcast.graph.builder import build_graph as build_podcast_graph
from src.ppt.graph.builder import build_graph as build_ppt_graph
from src.prompt_enhancer.graph.builder import build_graph as build_prompt_enhancer_graph
from src.prose.graph.builder import build_graph as build_prose_graph
from src.rag.builder import build_retriever
from src.rag.milvus import load_examples
from src.rag.retriever import Resource
from src.server.chat_request import (
    ChatRequest,
    EnhancePromptRequest,
    GeneratePodcastRequest,
    GeneratePPTRequest,
    GenerateProseRequest,
    TTSRequest,
)
from src.server.config_request import ConfigResponse
from src.server.mcp_request import MCPServerMetadataRequest, MCPServerMetadataResponse
from src.server.mcp_utils import load_mcp_tools
from src.server.rag_request import (
    RAGConfigResponse,
    RAGResourceRequest,
    RAGResourcesResponse,
)
from src.tools import VolcengineTTS
from src.utils.json_utils import sanitize_args
from src.utils.log_sanitizer import (
    sanitize_agent_name,
    sanitize_log_input,
    sanitize_thread_id,
    sanitize_tool_name,
    sanitize_user_content,
)

logger = logging.getLogger(__name__)

# Configure Windows event loop policy for PostgreSQL compatibility
# On Windows, psycopg requires a selector-based event loop, not the default ProactorEventLoop
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

INTERNAL_SERVER_ERROR_DETAIL = "Internal Server Error"

app = FastAPI(
    title="DeerFlow API",
    description="API for Deer",
    version="0.1.0",
)

# Add CORS middleware
# It's recommended to load the allowed origins from an environment variable
# for better security and flexibility across different environments.
allowed_origins_str = get_str_env("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

logger.info(f"Allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Restrict to specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Use the configured list of methods
    allow_headers=["*"],  # Now allow all headers, but can be restricted further
)

# Load examples into Milvus if configured
load_examples()

in_memory_store = InMemoryStore()
graph = build_graph_with_memory()

# Global ConversationFlowManager singleton to maintain session contexts
flow_manager = None


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    # Check if MCP server configuration is enabled
    mcp_enabled = get_bool_env("ENABLE_MCP_SERVER_CONFIGURATION", False)

    # Validate MCP settings if provided
    if request.mcp_settings and not mcp_enabled:
        raise HTTPException(
            status_code=403,
            detail="MCP server configuration is disabled. Set ENABLE_MCP_SERVER_CONFIGURATION=true to enable MCP features.",
        )

    thread_id = request.thread_id
    if thread_id == "__default__":
        thread_id = str(uuid4())

    return StreamingResponse(
        _astream_workflow_generator(
            request.model_dump()["messages"],
            thread_id,
            request.resources,
            request.max_plan_iterations,
            request.max_step_num,
            request.max_search_results,
            request.auto_accepted_plan,
            request.interrupt_feedback,
            request.mcp_settings if mcp_enabled else {},
            request.enable_background_investigation,
            request.report_style,
            request.enable_deep_thinking,
            request.enable_clarification,
            request.max_clarification_rounds,
            request.locale,
            request.interrupt_before_tools,
        ),
        media_type="text/event-stream",
    )


def _validate_tool_call_chunks(tool_call_chunks):
    """Validate and log tool call chunk structure for debugging."""
    if not tool_call_chunks:
        return
    
    logger.debug(f"Validating tool_call_chunks: count={len(tool_call_chunks)}")
    
    indices_seen = set()
    tool_ids_seen = set()
    
    for i, chunk in enumerate(tool_call_chunks):
        index = chunk.get("index")
        tool_id = chunk.get("id")
        name = chunk.get("name", "")
        has_args = "args" in chunk
        
        logger.debug(
            f"Chunk {i}: index={index}, id={tool_id}, name={name}, "
            f"has_args={has_args}, type={chunk.get('type')}"
        )
        
        if index is not None:
            indices_seen.add(index)
        if tool_id:
            tool_ids_seen.add(tool_id)
    
    if len(indices_seen) > 1:
        logger.debug(
            f"Multiple indices detected: {sorted(indices_seen)} - "
            f"This may indicate consecutive tool calls"
        )


def _process_tool_call_chunks(tool_call_chunks):
    """
    Process tool call chunks with proper index-based grouping.
    
    This function handles the concatenation of tool call chunks that belong
    to the same tool call (same index) while properly segregating chunks
    from different tool calls (different indices).
    
    The issue: In streaming, LangChain's ToolCallChunk concatenates string
    attributes (name, args) when chunks have the same index. We need to:
    1. Group chunks by index
    2. Detect index collisions with different tool names
    3. Accumulate arguments for the same index
    4. Return properly segregated tool calls
    """
    if not tool_call_chunks:
        return []
    
    _validate_tool_call_chunks(tool_call_chunks)
    
    chunks = []
    chunk_by_index = {}  # Group chunks by index to handle streaming accumulation
    
    for chunk in tool_call_chunks:
        index = chunk.get("index")
        chunk_id = chunk.get("id")
        
        if index is not None:
            # Create or update entry for this index
            if index not in chunk_by_index:
                chunk_by_index[index] = {
                    "name": "",
                    "args": "",
                    "id": chunk_id or "",
                    "index": index,
                    "type": chunk.get("type", ""),
                }
            
            # Validate and accumulate tool name
            chunk_name = chunk.get("name", "")
            if chunk_name:
                stored_name = chunk_by_index[index]["name"]
                
                # Check for index collision with different tool names
                if stored_name and stored_name != chunk_name:
                    logger.warning(
                        f"Tool name mismatch detected at index {index}: "
                        f"'{stored_name}' != '{chunk_name}'. "
                        f"This may indicate a streaming artifact or consecutive tool calls "
                        f"with the same index assignment."
                    )
                    # Keep the first name to prevent concatenation
                else:
                    chunk_by_index[index]["name"] = chunk_name
            
            # Update ID if new one provided
            if chunk_id and not chunk_by_index[index]["id"]:
                chunk_by_index[index]["id"] = chunk_id
            
            # Accumulate arguments
            if chunk.get("args"):
                chunk_by_index[index]["args"] += chunk.get("args", "")
        else:
            # Handle chunks without explicit index (edge case)
            logger.debug(f"Chunk without index encountered: {chunk}")
            chunks.append({
                "name": chunk.get("name", ""),
                "args": sanitize_args(chunk.get("args", "")),
                "id": chunk.get("id", ""),
                "index": 0,
                "type": chunk.get("type", ""),
            })
    
    # Convert indexed chunks to list, sorted by index for proper order
    for index in sorted(chunk_by_index.keys()):
        chunk_data = chunk_by_index[index]
        chunk_data["args"] = sanitize_args(chunk_data["args"])
        chunks.append(chunk_data)
        logger.debug(
            f"Processed tool call: index={index}, name={chunk_data['name']}, "
            f"id={chunk_data['id']}"
        )
    
    return chunks


def _get_agent_name(agent, message_metadata):
    """Extract agent name from agent tuple."""
    agent_name = "unknown"
    if agent and len(agent) > 0:
        agent_name = agent[0].split(":")[0] if ":" in agent[0] else agent[0]
    else:
        agent_name = message_metadata.get("langgraph_node", "unknown")
    return agent_name


def _create_event_stream_message(
    message_chunk, message_metadata, thread_id, agent_name
):
    """Create base event stream message."""
    content = message_chunk.content
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False)

    event_stream_message = {
        "thread_id": thread_id,
        "agent": agent_name,
        "id": message_chunk.id,
        "role": "assistant",
        "checkpoint_ns": message_metadata.get("checkpoint_ns", ""),
        "langgraph_node": message_metadata.get("langgraph_node", ""),
        "langgraph_path": message_metadata.get("langgraph_path", ""),
        "langgraph_step": message_metadata.get("langgraph_step", ""),
        "content": content,
    }

    # Add optional fields
    if message_chunk.additional_kwargs.get("reasoning_content"):
        event_stream_message["reasoning_content"] = message_chunk.additional_kwargs[
            "reasoning_content"
        ]

    if message_chunk.response_metadata.get("finish_reason"):
        event_stream_message["finish_reason"] = message_chunk.response_metadata.get(
            "finish_reason"
        )

    return event_stream_message


def _create_interrupt_event(thread_id, event_data):
    """Create interrupt event."""
    return _make_event(
        "interrupt",
        {
            "thread_id": thread_id,
            "id": event_data["__interrupt__"][0].ns[0],
            "role": "assistant",
            "content": event_data["__interrupt__"][0].value,
            "finish_reason": "interrupt",
            "options": [
                {"text": "Edit plan", "value": "edit_plan"},
                {"text": "Start research", "value": "accepted"},
            ],
        },
    )


def _process_initial_messages(message, thread_id):
    """Process initial messages and yield formatted events."""
    json_data = json.dumps(
        {
            "thread_id": thread_id,
            "id": "run--" + message.get("id", uuid4().hex),
            "role": "user",
            "content": message.get("content", ""),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    chat_stream_message(
        thread_id, f"event: message_chunk\ndata: {json_data}\n\n", "none"
    )


async def _process_message_chunk(message_chunk, message_metadata, thread_id, agent):
    """Process a single message chunk and yield appropriate events."""

    agent_name = _get_agent_name(agent, message_metadata)
    safe_agent_name = sanitize_agent_name(agent_name)
    safe_thread_id = sanitize_thread_id(thread_id)
    safe_agent = sanitize_agent_name(agent)
    logger.debug(f"[{safe_thread_id}] _process_message_chunk started for agent={safe_agent_name}")
    logger.debug(f"[{safe_thread_id}] Extracted agent_name: {safe_agent_name}")
    
    event_stream_message = _create_event_stream_message(
        message_chunk, message_metadata, thread_id, agent_name
    )

    if isinstance(message_chunk, ToolMessage):
        # Tool Message - Return the result of the tool call
        logger.debug(f"[{safe_thread_id}] Processing ToolMessage")
        tool_call_id = message_chunk.tool_call_id
        event_stream_message["tool_call_id"] = tool_call_id
        
        # Validate tool_call_id for debugging
        if tool_call_id:
            safe_tool_id = sanitize_log_input(tool_call_id, max_length=100)
            logger.debug(f"[{safe_thread_id}] ToolMessage with tool_call_id: {safe_tool_id}")
        else:
            logger.warning(f"[{safe_thread_id}] ToolMessage received without tool_call_id")
        
        logger.debug(f"[{safe_thread_id}] Yielding tool_call_result event")
        yield _make_event("tool_call_result", event_stream_message)
    elif isinstance(message_chunk, AIMessageChunk):
        # AI Message - Raw message tokens
        has_tool_calls = bool(message_chunk.tool_calls)
        has_chunks = bool(message_chunk.tool_call_chunks)
        logger.debug(f"[{safe_thread_id}] Processing AIMessageChunk, tool_calls={has_tool_calls}, tool_call_chunks={has_chunks}")
        
        if message_chunk.tool_calls:
            # AI Message - Tool Call (complete tool calls)
            safe_tool_names = [sanitize_tool_name(tc.get('name', 'unknown')) for tc in message_chunk.tool_calls]
            logger.debug(f"[{safe_thread_id}] AIMessageChunk has complete tool_calls: {safe_tool_names}")
            event_stream_message["tool_calls"] = message_chunk.tool_calls
            
            # Process tool_call_chunks with proper index-based grouping
            processed_chunks = _process_tool_call_chunks(
                message_chunk.tool_call_chunks
            )
            if processed_chunks:
                event_stream_message["tool_call_chunks"] = processed_chunks
                safe_chunk_names = [sanitize_tool_name(c.get('name')) for c in processed_chunks]
                logger.debug(
                    f"[{safe_thread_id}] Tool calls: {safe_tool_names}, "
                    f"Processed chunks: {len(processed_chunks)}"
                )
            
            logger.debug(f"[{safe_thread_id}] Yielding tool_calls event")
            yield _make_event("tool_calls", event_stream_message)
        elif message_chunk.tool_call_chunks:
            # AI Message - Tool Call Chunks (streaming)
            chunks_count = len(message_chunk.tool_call_chunks)
            logger.debug(f"[{safe_thread_id}] AIMessageChunk has streaming tool_call_chunks: {chunks_count} chunks")
            processed_chunks = _process_tool_call_chunks(
                message_chunk.tool_call_chunks
            )
            
            # Emit separate events for chunks with different indices (tool call boundaries)
            if processed_chunks:
                prev_chunk = None
                for chunk in processed_chunks:
                    current_index = chunk.get("index")
                    
                    # Log index transitions to detect tool call boundaries
                    if prev_chunk is not None and current_index != prev_chunk.get("index"):
                        prev_name = sanitize_tool_name(prev_chunk.get('name'))
                        curr_name = sanitize_tool_name(chunk.get('name'))
                        logger.debug(
                            f"[{safe_thread_id}] Tool call boundary detected: "
                            f"index {prev_chunk.get('index')} ({prev_name}) -> "
                            f"{current_index} ({curr_name})"
                        )
                    
                    prev_chunk = chunk
                
                # Include all processed chunks in the event
                event_stream_message["tool_call_chunks"] = processed_chunks
                safe_chunk_names = [sanitize_tool_name(c.get('name')) for c in processed_chunks]
                logger.debug(
                    f"[{safe_thread_id}] Streamed {len(processed_chunks)} tool call chunk(s): "
                    f"{safe_chunk_names}"
                )
            
            logger.debug(f"[{safe_thread_id}] Yielding tool_call_chunks event")
            yield _make_event("tool_call_chunks", event_stream_message)
        else:
            # AI Message - Raw message tokens
            content_len = len(message_chunk.content) if isinstance(message_chunk.content, str) else 0
            logger.debug(f"[{safe_thread_id}] AIMessageChunk is raw message tokens, content_len={content_len}")
            yield _make_event("message_chunk", event_stream_message)


async def _stream_graph_events(
    graph_instance, workflow_input, workflow_config, thread_id
):
    """Stream events from the graph and process them."""
    safe_thread_id = sanitize_thread_id(thread_id)
    logger.debug(f"[{safe_thread_id}] Starting graph event stream with agent nodes")
    try:
        event_count = 0
        async for agent, _, event_data in graph_instance.astream(
            workflow_input,
            config=workflow_config,
            stream_mode=["messages", "updates"],
            subgraphs=True,
        ):
            event_count += 1
            safe_agent = sanitize_agent_name(agent)
            logger.debug(f"[{safe_thread_id}] Graph event #{event_count} received from agent: {safe_agent}")
            
            if isinstance(event_data, dict):
                if "__interrupt__" in event_data:
                    logger.debug(
                        f"[{safe_thread_id}] Processing interrupt event: "
                        f"ns={getattr(event_data['__interrupt__'][0], 'ns', 'unknown') if isinstance(event_data['__interrupt__'], (list, tuple)) and len(event_data['__interrupt__']) > 0 else 'unknown'}, "
                        f"value_len={len(getattr(event_data['__interrupt__'][0], 'value', '')) if isinstance(event_data['__interrupt__'], (list, tuple)) and len(event_data['__interrupt__']) > 0 and hasattr(event_data['__interrupt__'][0], 'value') and hasattr(event_data['__interrupt__'][0].value, '__len__') else 'unknown'}"
                    )
                    yield _create_interrupt_event(thread_id, event_data)
                logger.debug(f"[{safe_thread_id}] Dict event without interrupt, skipping")
                continue

            message_chunk, message_metadata = cast(
                tuple[BaseMessage, dict[str, Any]], event_data
            )
            
            safe_node = sanitize_agent_name(message_metadata.get('langgraph_node', 'unknown'))
            safe_step = sanitize_log_input(message_metadata.get('langgraph_step', 'unknown'))
            logger.debug(
                f"[{safe_thread_id}] Processing message chunk: "
                f"type={type(message_chunk).__name__}, "
                f"node={safe_node}, "
                f"step={safe_step}"
            )

            async for event in _process_message_chunk(
                message_chunk, message_metadata, thread_id, agent
            ):
                yield event
        
        logger.debug(f"[{safe_thread_id}] Graph event stream completed. Total events: {event_count}")
    except Exception as e:
        logger.exception(f"[{safe_thread_id}] Error during graph execution")
        yield _make_event(
            "error",
            {
                "thread_id": thread_id,
                "error": "Error during graph execution",
            },
        )


async def _astream_workflow_generator(
    messages: List[dict],
    thread_id: str,
    resources: List[Resource],
    max_plan_iterations: int,
    max_step_num: int,
    max_search_results: int,
    auto_accepted_plan: bool,
    interrupt_feedback: str,
    mcp_settings: dict,
    enable_background_investigation: bool,
    report_style: ReportStyle,
    enable_deep_thinking: bool,
    enable_clarification: bool,
    max_clarification_rounds: int,
    locale: str = "en-US",
    interrupt_before_tools: Optional[List[str]] = None,
):
    safe_thread_id = sanitize_thread_id(thread_id)
    safe_feedback = sanitize_log_input(interrupt_feedback) if interrupt_feedback else ""
    logger.debug(
        f"[{safe_thread_id}] _astream_workflow_generator starting: "
        f"messages_count={len(messages)}, "
        f"auto_accepted_plan={auto_accepted_plan}, "
        f"interrupt_feedback={safe_feedback}, "
        f"interrupt_before_tools={interrupt_before_tools}"
    )
    
    # Process initial messages
    logger.debug(f"[{safe_thread_id}] Processing {len(messages)} initial messages")
    for message in messages:
        if isinstance(message, dict) and "content" in message:
            safe_content = sanitize_user_content(message.get('content', ''))
            logger.debug(f"[{safe_thread_id}] Sending initial message to client: {safe_content}")
            _process_initial_messages(message, thread_id)

    logger.debug(f"[{safe_thread_id}] Reconstructing clarification history")
    clarification_history = reconstruct_clarification_history(messages)

    logger.debug(f"[{safe_thread_id}] Building clarified topic from history")
    clarified_topic, clarification_history = build_clarified_topic_from_history(
        clarification_history
    )
    latest_message_content = messages[-1]["content"] if messages else ""
    clarified_research_topic = clarified_topic or latest_message_content
    safe_topic = sanitize_user_content(clarified_research_topic)
    logger.debug(f"[{safe_thread_id}] Clarified research topic: {safe_topic}")

    # Prepare workflow input
    logger.debug(f"[{safe_thread_id}] Preparing workflow input")
    workflow_input = {
        "messages": messages,
        "plan_iterations": 0,
        "final_report": "",
        "current_plan": None,
        "observations": [],
        "auto_accepted_plan": auto_accepted_plan,
        "enable_background_investigation": enable_background_investigation,
        "research_topic": latest_message_content,
        "clarification_history": clarification_history,
        "clarified_research_topic": clarified_research_topic,
        "enable_clarification": enable_clarification,
        "max_clarification_rounds": max_clarification_rounds,
        "locale": locale,
    }

    if not auto_accepted_plan and interrupt_feedback:
        logger.debug(f"[{safe_thread_id}] Creating resume command with interrupt_feedback: {safe_feedback}")
        resume_msg = f"[{interrupt_feedback}]"
        if messages:
            resume_msg += f" {messages[-1]['content']}"
        workflow_input = Command(resume=resume_msg)

    # Prepare workflow config
    logger.debug(
        f"[{safe_thread_id}] Preparing workflow config: "
        f"max_plan_iterations={max_plan_iterations}, "
        f"max_step_num={max_step_num}, "
        f"report_style={report_style.value}, "
        f"enable_deep_thinking={enable_deep_thinking}"
    )
    workflow_config = {
        "thread_id": thread_id,
        "resources": resources,
        "max_plan_iterations": max_plan_iterations,
        "max_step_num": max_step_num,
        "max_search_results": max_search_results,
        "mcp_settings": mcp_settings,
        "report_style": report_style.value,
        "enable_deep_thinking": enable_deep_thinking,
        "interrupt_before_tools": interrupt_before_tools,
        "recursion_limit": get_recursion_limit(),
    }

    checkpoint_saver = get_bool_env("LANGGRAPH_CHECKPOINT_SAVER", False)
    checkpoint_url = get_str_env("LANGGRAPH_CHECKPOINT_DB_URL", "")
    
    logger.debug(
        f"[{safe_thread_id}] Checkpoint configuration: "
        f"saver_enabled={checkpoint_saver}, "
        f"url_configured={bool(checkpoint_url)}"
    )
    
    # Handle checkpointer if configured
    connection_kwargs = {
        "autocommit": True,
        "row_factory": "dict_row",
        "prepare_threshold": 0,
    }
    if checkpoint_saver and checkpoint_url != "":
        if checkpoint_url.startswith("postgresql://"):
            logger.info(f"[{safe_thread_id}] Starting async postgres checkpointer")
            logger.debug(f"[{safe_thread_id}] Setting up PostgreSQL connection pool")
            async with AsyncConnectionPool(
                checkpoint_url, kwargs=connection_kwargs
            ) as conn:
                logger.debug(f"[{safe_thread_id}] Initializing AsyncPostgresSaver")
                checkpointer = AsyncPostgresSaver(conn)
                await checkpointer.setup()
                logger.debug(f"[{safe_thread_id}] Attaching checkpointer to graph")
                graph.checkpointer = checkpointer
                graph.store = in_memory_store
                logger.debug(f"[{safe_thread_id}] Starting to stream graph events")
                async for event in _stream_graph_events(
                    graph, workflow_input, workflow_config, thread_id
                ):
                    yield event
                logger.debug(f"[{safe_thread_id}] Graph event streaming completed")

        if checkpoint_url.startswith("mongodb://"):
            logger.info(f"[{safe_thread_id}] Starting async mongodb checkpointer")
            logger.debug(f"[{safe_thread_id}] Setting up MongoDB connection")
            async with AsyncMongoDBSaver.from_conn_string(
                checkpoint_url
            ) as checkpointer:
                logger.debug(f"[{safe_thread_id}] Attaching MongoDB checkpointer to graph")
                graph.checkpointer = checkpointer
                graph.store = in_memory_store
                logger.debug(f"[{safe_thread_id}] Starting to stream graph events")
                async for event in _stream_graph_events(
                    graph, workflow_input, workflow_config, thread_id
                ):
                    yield event
                logger.debug(f"[{safe_thread_id}] Graph event streaming completed")
    else:
        logger.debug(f"[{safe_thread_id}] No checkpointer configured, using in-memory graph")
        # Use graph without MongoDB checkpointer
        logger.debug(f"[{safe_thread_id}] Starting to stream graph events")
        async for event in _stream_graph_events(
            graph, workflow_input, workflow_config, thread_id
        ):
            yield event
        logger.debug(f"[{safe_thread_id}] Graph event streaming completed")


def _make_event(event_type: str, data: dict[str, any]):
    if data.get("content") == "":
        data.pop("content")
    # Ensure JSON serialization with proper encoding
    try:
        json_data = json.dumps(data, ensure_ascii=False)

        finish_reason = data.get("finish_reason", "")
        chat_stream_message(
            data.get("thread_id", ""),
            f"event: {event_type}\ndata: {json_data}\n\n",
            finish_reason,
        )

        return f"event: {event_type}\ndata: {json_data}\n\n"
    except (TypeError, ValueError) as e:
        logger.error(f"Error serializing event data: {e}")
        # Return a safe error event
        error_data = json.dumps({"error": "Serialization failed"}, ensure_ascii=False)
        return f"event: error\ndata: {error_data}\n\n"


@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """Convert text to speech using volcengine TTS API."""
    app_id = get_str_env("VOLCENGINE_TTS_APPID", "")
    if not app_id:
        raise HTTPException(status_code=400, detail="VOLCENGINE_TTS_APPID is not set")
    access_token = get_str_env("VOLCENGINE_TTS_ACCESS_TOKEN", "")
    if not access_token:
        raise HTTPException(
            status_code=400, detail="VOLCENGINE_TTS_ACCESS_TOKEN is not set"
        )

    try:
        cluster = get_str_env("VOLCENGINE_TTS_CLUSTER", "volcano_tts")
        voice_type = get_str_env("VOLCENGINE_TTS_VOICE_TYPE", "BV700_V2_streaming")

        tts_client = VolcengineTTS(
            appid=app_id,
            access_token=access_token,
            cluster=cluster,
            voice_type=voice_type,
        )
        # Call the TTS API
        result = tts_client.text_to_speech(
            text=request.text[:1024],
            encoding=request.encoding,
            speed_ratio=request.speed_ratio,
            volume_ratio=request.volume_ratio,
            pitch_ratio=request.pitch_ratio,
            text_type=request.text_type,
            with_frontend=request.with_frontend,
            frontend_type=request.frontend_type,
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=str(result["error"]))

        # Decode the base64 audio data
        audio_data = base64.b64decode(result["audio_data"])

        # Return the audio file
        return Response(
            content=audio_data,
            media_type=f"audio/{request.encoding}",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=tts_output.{request.encoding}"
                )
            },
        )

    except Exception as e:
        logger.exception(f"Error in TTS endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/podcast/generate")
async def generate_podcast(request: GeneratePodcastRequest):
    try:
        report_content = request.content
        print(report_content)
        workflow = build_podcast_graph()
        final_state = workflow.invoke({"input": report_content})
        audio_bytes = final_state["output"]
        return Response(content=audio_bytes, media_type="audio/mp3")
    except Exception as e:
        logger.exception(f"Error occurred during podcast generation: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/ppt/generate")
async def generate_ppt(request: GeneratePPTRequest):
    try:
        report_content = request.content
        print(report_content)
        workflow = build_ppt_graph()
        final_state = workflow.invoke({"input": report_content})
        generated_file_path = final_state["generated_file_path"]
        with open(generated_file_path, "rb") as f:
            ppt_bytes = f.read()
        return Response(
            content=ppt_bytes,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
    except Exception as e:
        logger.exception(f"Error occurred during ppt generation: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/prose/generate")
async def generate_prose(request: GenerateProseRequest):
    try:
        sanitized_prompt = request.prompt.replace("\r\n", "").replace("\n", "")
        logger.info(f"Generating prose for prompt: {sanitized_prompt}")
        workflow = build_prose_graph()
        events = workflow.astream(
            {
                "content": request.prompt,
                "option": request.option,
                "command": request.command,
            },
            stream_mode="messages",
            subgraphs=True,
        )
        return StreamingResponse(
            (f"data: {event[0].content}\n\n" async for _, event in events),
            media_type="text/event-stream",
        )
    except Exception as e:
        logger.exception(f"Error occurred during prose generation: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/prompt/enhance")
async def enhance_prompt(request: EnhancePromptRequest):
    try:
        sanitized_prompt = request.prompt.replace("\r\n", "").replace("\n", "")
        logger.info(f"Enhancing prompt: {sanitized_prompt}")

        # Convert string report_style to ReportStyle enum
        report_style = None
        if request.report_style:
            try:
                # Handle both uppercase and lowercase input
                style_mapping = {
                    "ACADEMIC": ReportStyle.ACADEMIC,
                    "POPULAR_SCIENCE": ReportStyle.POPULAR_SCIENCE,
                    "NEWS": ReportStyle.NEWS,
                    "SOCIAL_MEDIA": ReportStyle.SOCIAL_MEDIA,
                    "STRATEGIC_INVESTMENT": ReportStyle.STRATEGIC_INVESTMENT,
                }
                report_style = style_mapping.get(
                    request.report_style.upper(), ReportStyle.ACADEMIC
                )
            except Exception:
                # If invalid style, default to ACADEMIC
                report_style = ReportStyle.ACADEMIC
        else:
            report_style = ReportStyle.ACADEMIC

        workflow = build_prompt_enhancer_graph()
        final_state = workflow.invoke(
            {
                "prompt": request.prompt,
                "context": request.context,
                "report_style": report_style,
            }
        )
        return {"result": final_state["output"]}
    except Exception as e:
        logger.exception(f"Error occurred during prompt enhancement: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/mcp/server/metadata", response_model=MCPServerMetadataResponse)
async def mcp_server_metadata(request: MCPServerMetadataRequest):
    """Get information about an MCP server."""
    # Check if MCP server configuration is enabled
    if not get_bool_env("ENABLE_MCP_SERVER_CONFIGURATION", False):
        raise HTTPException(
            status_code=403,
            detail="MCP server configuration is disabled. Set ENABLE_MCP_SERVER_CONFIGURATION=true to enable MCP features.",
        )

    try:
        # Set default timeout with a longer value for this endpoint
        timeout = 300  # Default to 300 seconds for this endpoint

        # Use custom timeout from request if provided
        if request.timeout_seconds is not None:
            timeout = request.timeout_seconds

        # Load tools from the MCP server using the utility function
        tools = await load_mcp_tools(
            server_type=request.transport,
            command=request.command,
            args=request.args,
            url=request.url,
            env=request.env,
            headers=request.headers,
            timeout_seconds=timeout,
        )

        # Create the response with tools
        response = MCPServerMetadataResponse(
            transport=request.transport,
            command=request.command,
            args=request.args,
            url=request.url,
            env=request.env,
            headers=request.headers,
            tools=tools,
        )

        return response
    except Exception as e:
        logger.exception(f"Error in MCP server metadata endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.get("/api/rag/config", response_model=RAGConfigResponse)
async def rag_config():
    """Get the config of the RAG."""
    return RAGConfigResponse(provider=SELECTED_RAG_PROVIDER)


@app.get("/api/rag/resources", response_model=RAGResourcesResponse)
async def rag_resources(request: Annotated[RAGResourceRequest, Query()]):
    """Get the resources of the RAG."""
    retriever = build_retriever()
    if retriever:
        return RAGResourcesResponse(resources=retriever.list_resources(request.query))
    return RAGResourcesResponse(resources=[])


@app.get("/api/config", response_model=ConfigResponse)
async def config():
    """Get the config of the server."""
    return ConfigResponse(
        rag=RAGConfigResponse(provider=SELECTED_RAG_PROVIDER),
        models=get_configured_llm_models(),
    )

# Project Management Agent API endpoints
# NOTE: Legacy PostgreSQL REST endpoints removed - all PM operations now go through /api/pm/chat/stream
# This endpoint uses PM Providers (OpenProject, JIRA, etc.) instead of local database

# PM REST endpoints for UI data fetching
@app.get("/api/pm/projects")
async def pm_list_projects(request: Request):
    """List all projects from PM provider"""
    try:
        from src.conversation.flow_manager import ConversationFlowManager
        from database.connection import get_db_session
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        # Use global flow manager to access PM provider
        global flow_manager
        if flow_manager is None:
            flow_manager = ConversationFlowManager(db_session=db)
        fm = flow_manager
        
        if not fm.pm_provider:
            raise HTTPException(status_code=503, detail="PM Provider not configured")
        
        projects = await fm.pm_provider.list_projects()
        
        # Convert to dict format for JSON response
        return [
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
            }
            for p in projects
        ]
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/projects/{project_id}/tasks")
async def pm_list_tasks(request: Request, project_id: str):
    """List all tasks for a project"""
    try:
        from src.conversation.flow_manager import ConversationFlowManager
        from database.connection import get_db_session
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        global flow_manager
        if flow_manager is None:
            flow_manager = ConversationFlowManager(db_session=db)
        fm = flow_manager
        
        if not fm.pm_provider:
            raise HTTPException(status_code=503, detail="PM Provider not configured")
        
        tasks = await fm.pm_provider.list_tasks(project_id=project_id)
        
        # Build assignee map if needed
        assignee_map = {}
        for task in tasks:
            if task.assignee_id and task.assignee_id not in assignee_map:
                try:
                    user = await fm.pm_provider.get_user(task.assignee_id)
                    if user:
                        assignee_map[task.assignee_id] = user.name
                except:
                    pass
        
        return [
            {
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "status": t.status.value if hasattr(t.status, 'value') else str(t.status),
                "priority": t.priority.value if hasattr(t.priority, 'value') else str(t.priority),
                "estimated_hours": t.estimated_hours,
                "assigned_to": assignee_map.get(t.assignee_id) if t.assignee_id else None,
            }
            for t in tasks
        ]
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/tasks/my")
async def pm_list_my_tasks(request: Request):
    """List tasks assigned to current user"""
    try:
        from src.conversation.flow_manager import ConversationFlowManager
        from database.connection import get_db_session
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        global flow_manager
        if flow_manager is None:
            flow_manager = ConversationFlowManager(db_session=db)
        fm = flow_manager
        
        if not fm.pm_provider:
            raise HTTPException(status_code=503, detail="PM Provider not configured")
        
        # Get current user
        current_user = await fm.pm_provider.get_current_user()
        if not current_user:
            raise HTTPException(status_code=401, detail="Cannot determine current user")
        
        tasks = await fm.pm_provider.list_tasks(assignee_id=str(current_user.id))
        
        # Fetch all projects for name mapping
        all_projects = await fm.pm_provider.list_projects()
        project_map = {p.id: p.name for p in all_projects}
        
        return [
            {
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "status": t.status.value if hasattr(t.status, 'value') else str(t.status),
                "priority": t.priority.value if hasattr(t.priority, 'value') else str(t.priority),
                "estimated_hours": t.estimated_hours,
                "project_name": project_map.get(t.project_id, "Unknown") if t.project_id else "Unknown",
            }
            for t in tasks
        ]
    except Exception as e:
        logger.error(f"Failed to list my tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/tasks/all")
async def pm_list_all_tasks(request: Request):
    """List all tasks across all projects"""
    try:
        from src.conversation.flow_manager import ConversationFlowManager
        from database.connection import get_db_session
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        global flow_manager
        if flow_manager is None:
            flow_manager = ConversationFlowManager(db_session=db)
        fm = flow_manager
        
        if not fm.pm_provider:
            raise HTTPException(status_code=503, detail="PM Provider not configured")
        
        # Get all tasks without filtering by assignee
        tasks = await fm.pm_provider.list_tasks()
        
        # Fetch all projects for name mapping
        all_projects = await fm.pm_provider.list_projects()
        project_map = {p.id: p.name for p in all_projects}
        
        return [
            {
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "status": t.status.value if hasattr(t.status, 'value') else str(t.status),
                "priority": t.priority.value if hasattr(t.priority, 'value') else str(t.priority),
                "estimated_hours": t.estimated_hours,
                "project_name": project_map.get(t.project_id, "Unknown") if t.project_id else "Unknown",
            }
            for t in tasks
        ]
    except Exception as e:
        logger.error(f"Failed to list all tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/projects/{project_id}/sprints")
async def pm_list_sprints(request: Request, project_id: str):
    """List all sprints for a project"""
    try:
        from src.conversation.flow_manager import ConversationFlowManager
        from database.connection import get_db_session
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        global flow_manager
        if flow_manager is None:
            flow_manager = ConversationFlowManager(db_session=db)
        fm = flow_manager
        
        if not fm.pm_provider:
            raise HTTPException(status_code=503, detail="PM Provider not configured")
        
        sprints = await fm.pm_provider.list_sprints(project_id=project_id)
        
        return [
            {
                "id": str(s.id),
                "name": s.name,
                "start_date": s.start_date.isoformat() if s.start_date else None,
                "end_date": s.end_date.isoformat() if s.end_date else None,
                "status": s.status.value if hasattr(s.status, 'value') else str(s.status),
            }
            for s in sprints
        ]
    except Exception as e:
        logger.error(f"Failed to list sprints: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# PM Chat endpoint
@app.post("/api/pm/chat/stream")
async def pm_chat_stream(request: Request):
    """Stream chat responses for Project Management tasks"""
    try:
        from src.conversation.flow_manager import ConversationFlowManager
        from src.workflow import run_agent_workflow_stream
        from database.connection import get_db_session
        from sqlalchemy.orm import Session
        from fastapi import Depends
        from fastapi.responses import StreamingResponse
        import asyncio
        import json
        import uuid
        import time
            
        body = await request.json()
        user_message = body.get("messages", [{}])[0].get("content", "")
        thread_id = body.get("thread_id", str(uuid.uuid4()))
            
        # Get database session
        db_gen = get_db_session()
        db = next(db_gen)
            
        try:
            # Use global flow manager singleton to maintain session contexts
            global flow_manager
            if flow_manager is None:
                flow_manager = ConversationFlowManager(db_session=db)
                logger.info("Created global ConversationFlowManager singleton")
            fm = flow_manager
                
            async def generate_stream() -> AsyncIterator[str]:
                """Generate SSE stream of chat responses with progress updates"""
                api_start = time.time()
                logger.info(f"[PM-CHAT-TIMING] generate_stream started")
                    
                try:
                    # First, generate PM plan to check if CREATE_WBS is needed
                    plan_start = time.time()
                    temp_context = fm._get_or_create_context(thread_id)
                    pm_plan = await fm.generate_pm_plan(user_message, temp_context)
                    logger.info(f"[PM-CHAT-TIMING] PM plan generated: {time.time() - plan_start:.2f}s")
                        
                    # Check if plan has CREATE_WBS steps that need research
                    needs_research = False
                    if pm_plan and pm_plan.get('steps'):
                        for step in pm_plan.get('steps', []):
                            if step.get('step_type') == 'create_wbs':
                                needs_research = True
                                break
                        
                    logger.info(f"[PM-CHAT-TIMING] Needs research: {needs_research} - {time.time() - api_start:.2f}s")
                        
                    # For research queries, stream DeerFlow updates
                    if needs_research:
                        initial_chunk = {
                            "id": str(uuid.uuid4()),
                            "thread_id": thread_id,
                            "agent": "coordinator",
                            "role": "assistant",
                            "content": "🦌 **Starting DeerFlow research...**\n\n",
                            "finish_reason": None
                        }
                        yield "event: message_chunk\n"
                        yield f"data: {json.dumps(initial_chunk)}\n\n"
                            
                        try:
                            # Let LLM extract project name from full context
                            research_query = f"Research typical phases, deliverables, and tasks based on the user's request: {user_message}. Focus on project structure and common components."
                                
                            research_start = time.time()
                            logger.info(f"[PM-CHAT-TIMING] Starting DeerFlow research: {time.time() - api_start:.2f}s")
                            final_research_state = None
                                
                            # Use _astream_workflow_generator to get properly formatted research events
                            from src.config.report_style import ReportStyle
                                
                            async for event in _astream_workflow_generator(
                                messages=[{"role": "user", "content": research_query}],
                                thread_id=thread_id,
                                resources=[],
                                max_plan_iterations=1,
                                max_step_num=3,
                                max_search_results=3,
                                auto_accepted_plan=True,
                                interrupt_feedback="",
                                mcp_settings={},
                                enable_background_investigation=True,
                                report_style=ReportStyle.ACADEMIC,
                                enable_deep_thinking=False,
                                enable_clarification=False,
                                max_clarification_rounds=3,
                                locale="en-US",
                                interrupt_before_tools=None
                            ):
                                # Yield formatted DeerFlow events directly
                                yield event
                                
                            # Collect final state for storing research context
                            final_research_state = {"final_report": "Research completed"}
                                
                            # Store research result
                            if final_research_state:
                                from src.conversation.flow_manager import ConversationContext, FlowState, IntentType
                                from datetime import datetime
                                    
                                if thread_id not in fm.contexts:
                                    fm.contexts[thread_id] = ConversationContext(
                                        session_id=thread_id,
                                        current_state=FlowState.INTENT_DETECTION,
                                        intent=IntentType.UNKNOWN,
                                        gathered_data={},
                                        required_fields=[],
                                        conversation_history=[],
                                        created_at=datetime.now(),
                                        updated_at=datetime.now()
                                    )
                                    
                                context = fm.contexts[thread_id]
                                context.gathered_data['research_context'] = "Research completed"
                                context.gathered_data['research_already_done'] = True
                                logger.info(f"Stored research result in context for session {thread_id}")
                                
                            research_duration = time.time() - research_start
                            logger.info(f"[PM-CHAT-TIMING] DeerFlow research completed: {research_duration:.2f}s")
                            
                        except Exception as research_error:
                            logger.error(f"DeerFlow streaming failed: {research_error}")
                            import traceback
                            logger.error(traceback.format_exc())
                        
                    # Create queue to collect streaming chunks
                    stream_queue = asyncio.Queue()
                        
                    async def stream_callback(content: str):
                        """Callback to capture streaming chunks"""
                        await stream_queue.put(content)
                        
                    async def process_with_streaming():
                        try:
                            process_start = time.time()
                            logger.info(f"[PM-CHAT-TIMING] process_with_streaming started: {time.time() - api_start:.2f}s")
                            response = await fm.process_message(
                                message=user_message,
                                session_id=thread_id,
                                user_id="f430f348-d65f-427f-9379-3d0f163393d1",
                                stream_callback=stream_callback
                            )
                            logger.info(f"[PM-CHAT-TIMING] process_message completed: {time.time() - process_start:.2f}s")
                            await stream_queue.put(None)
                            return response
                        except Exception as e:
                            logger.error(f"Error in process_message: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                            error_msg = f"❌ Error processing request: {str(e)}"
                            await stream_callback(error_msg)
                            await stream_queue.put(None)
                            return {
                                "type": "error",
                                "message": error_msg,
                                "state": "error"
                            }
                        
                    process_task = asyncio.create_task(process_with_streaming())
                    logger.info(f"[PM-CHAT-TIMING] process_task started: {time.time() - api_start:.2f}s")
                        
                    while True:
                        try:
                            chunk = await asyncio.wait_for(stream_queue.get(), timeout=1.0)
                            if chunk is None:
                                break
                                
                            chunk_data = {
                                "id": str(uuid.uuid4()),
                                "thread_id": thread_id,
                                "agent": "coordinator",
                                "role": "assistant",
                                "content": chunk,
                                "finish_reason": None
                            }
                            yield "event: message_chunk\n"
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                        except asyncio.TimeoutError:
                            if process_task.done():
                                break
                            continue
                        
                    try:
                        response = await process_task
                    except Exception as task_error:
                        logger.error(f"Task execution failed: {task_error}")
                        import traceback
                        logger.error(traceback.format_exc())
                        response = {
                            "type": "error",
                            "message": f"❌ Task execution failed: {str(task_error)}",
                            "state": "error"
                        }
                        
                    if response:
                        response_message = response.get('message', '')
                        response_state = response.get('state', 'complete')
                        response_type = response.get('type', 'execution_completed')
                        finish_reason = None
                        if response_type == 'error':
                            finish_reason = "error"
                        elif response_state == 'complete' or response_state == 'completed':
                            finish_reason = "stop"
                        elif '?' in response_message or 'specify' in response_message.lower():
                            finish_reason = "interrupt"
                        else:
                            finish_reason = "stop"
                    else:
                        finish_reason = "error"
                        response_message = "❌ No response received from processing"
                        
                    chunk_data = {
                        "id": str(uuid.uuid4()),
                        "thread_id": thread_id,
                        "agent": "coordinator",
                        "role": "assistant",
                        "content": "",
                        "finish_reason": finish_reason
                    }
                    logger.info(f"[PM-CHAT-TIMING] Sending finish event: finish_reason={finish_reason}, response_type={response_type if response else 'None'}")
                    yield "event: message_chunk\n"
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                        
                    logger.info(f"[PM-CHAT-TIMING] Total response time: {time.time() - api_start:.2f}s")
                    
                except Exception as e:
                    error_message = f"Error: {str(e)}"
                    error_data = {
                        "id": str(uuid.uuid4()),
                        "thread_id": thread_id,
                        "agent": "coordinator",
                        "role": "assistant",
                        "content": error_message,
                        "finish_reason": "stop"
                    }
                    yield "event: message_chunk\n"
                    yield f"data: {json.dumps(error_data)}\n\n"
                
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no"
                }
            )
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"PM chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
