# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import asyncio
import base64
import json
import logging
import os
from typing import Annotated, Any, AsyncIterator, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
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
from src.prompt_enhancer.graph.builder import (
    build_graph as build_prompt_enhancer_graph
)
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
from src.server.mcp_request import (
    MCPServerMetadataRequest,
    MCPServerMetadataResponse,
)
from src.server.mcp_utils import load_mcp_tools
from src.server.rag_request import (
    RAGConfigResponse,
    RAGResourceRequest,
    RAGResourcesResponse,
)
from src.server.pm_provider_request import (
    ProjectImportRequest,
    ProviderUpdateRequest,
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
# On Windows, psycopg requires a selector-based event loop,
# not the default ProactorEventLoop
if os.name == "nt":
    # WindowsSelectorEventLoopPolicy is available on Windows
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()  # type: ignore
    )

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
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
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
            detail=(
                "MCP server configuration is disabled. "
                "Set ENABLE_MCP_SERVER_CONFIGURATION=true to enable "
                "MCP features."
            ),
        )

    thread_id = request.thread_id or "__default__"
    if thread_id == "__default__":
        thread_id = str(uuid4())

    return StreamingResponse(
        _astream_workflow_generator(
            request.model_dump()["messages"],
            thread_id,
            request.resources or [],
            request.max_plan_iterations or 1,
            request.max_step_num or 3,
            request.max_search_results or 3,
            request.auto_accepted_plan or False,
            request.interrupt_feedback or "",
            (request.mcp_settings if mcp_enabled else {}) or {},
            request.enable_background_investigation or True,
            request.report_style or ReportStyle.ACADEMIC,
            request.enable_deep_thinking or False,
            request.enable_clarification or False,
            request.max_clarification_rounds or 3,
            request.locale or "en-US",
            request.interrupt_before_tools or [],
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
    # Group chunks by index to handle streaming accumulation
    chunk_by_index = {}
    
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
                        f"This may indicate a streaming artifact or "
                        f"consecutive tool calls with the same "
                        f"index assignment."
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
        event_stream_message["reasoning_content"] = (
            message_chunk.additional_kwargs["reasoning_content"]
        )

    # Include finish_reason from response_metadata or message_metadata
    finish_reason = (
        message_chunk.response_metadata.get("finish_reason")
        or message_metadata.get("finish_reason")
    )
    if finish_reason:
        event_stream_message["finish_reason"] = finish_reason

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
        thread_id,
        f"event: message_chunk\ndata: {json_data}\n\n",
        "none"
    )


async def _process_message_chunk(
    message_chunk, message_metadata, thread_id, agent
):
    """Process a single message chunk and yield appropriate events."""

    agent_name = _get_agent_name(agent, message_metadata)
    safe_agent_name = sanitize_agent_name(agent_name)
    safe_thread_id = sanitize_thread_id(thread_id)
    logger.debug(
        f"[{safe_thread_id}] _process_message_chunk started for "
        f"agent={safe_agent_name}"
    )
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
            logger.debug(
                f"[{safe_thread_id}] ToolMessage with tool_call_id: "
                f"{safe_tool_id}"
            )
        else:
            logger.warning(
                f"[{safe_thread_id}] ToolMessage received without tool_call_id"
            )
        
        logger.debug(f"[{safe_thread_id}] Yielding tool_call_result event")
        yield _make_event("tool_call_result", event_stream_message)
    elif isinstance(message_chunk, AIMessageChunk):
        # AI Message - Raw message tokens
        has_tool_calls = bool(message_chunk.tool_calls)
        has_chunks = bool(message_chunk.tool_call_chunks)
        logger.debug(
            f"[{safe_thread_id}] Processing AIMessageChunk, "
            f"tool_calls={has_tool_calls}, tool_call_chunks={has_chunks}"
        )

        if message_chunk.tool_calls:
            # AI Message - Tool Call (complete tool calls)
            safe_tool_names = [
                sanitize_tool_name(tc.get('name', 'unknown'))
                for tc in message_chunk.tool_calls
            ]
            logger.debug(
                f"[{safe_thread_id}] AIMessageChunk has complete tool_calls: "
                f"{safe_tool_names}"
            )
            event_stream_message["tool_calls"] = message_chunk.tool_calls
            
            # Process tool_call_chunks with proper index-based grouping
            processed_chunks = _process_tool_call_chunks(
                message_chunk.tool_call_chunks
            )
            if processed_chunks:
                event_stream_message["tool_call_chunks"] = processed_chunks
                safe_chunk_names = [
                    sanitize_tool_name(c.get('name'))
                    for c in processed_chunks
                ]
                logger.debug(
                    f"[{safe_thread_id}] Tool calls: {safe_tool_names}, "
                    f"Processed chunks: {len(processed_chunks)}"
                )
            
            logger.debug(f"[{safe_thread_id}] Yielding tool_calls event")
            yield _make_event("tool_calls", event_stream_message)
        elif message_chunk.tool_call_chunks:
            # AI Message - Tool Call Chunks (streaming)
            chunks_count = len(message_chunk.tool_call_chunks)
            logger.debug(
                f"[{safe_thread_id}] AIMessageChunk has streaming "
                f"tool_call_chunks: {chunks_count} chunks"
            )
            processed_chunks = _process_tool_call_chunks(
                message_chunk.tool_call_chunks
            )
            
            # Emit separate events for chunks with different indices
            # (tool call boundaries)
            if processed_chunks:
                prev_chunk = None
                for chunk in processed_chunks:
                    current_index = chunk.get("index")
                    
                    # Log index transitions to detect tool call boundaries
                    if prev_chunk is not None and (
                        current_index != prev_chunk.get("index")
                    ):
                        prev_name = sanitize_tool_name(prev_chunk.get('name'))
                        curr_name = sanitize_tool_name(chunk.get('name'))
                        logger.debug(
                            f"[{safe_thread_id}] Tool call boundary detected: "
                            f"index {prev_chunk.get('index')} "
                            f"({prev_name}) -> {current_index} ({curr_name})"
                        )
                    
                    prev_chunk = chunk
                
                # Include all processed chunks in the event
                event_stream_message["tool_call_chunks"] = processed_chunks
                safe_chunk_names = [
                    sanitize_tool_name(c.get('name'))
                    for c in processed_chunks
                ]
                logger.debug(
                    f"[{safe_thread_id}] Streamed {len(processed_chunks)} "
                    f"tool call chunk(s): {safe_chunk_names}"
                )
            
            logger.debug(f"[{safe_thread_id}] Yielding tool_call_chunks event")
            yield _make_event("tool_call_chunks", event_stream_message)
        else:
            # AI Message - Raw message tokens
            content_len = (
                len(message_chunk.content)
                if isinstance(message_chunk.content, str)
                else 0
            )
            logger.debug(
                f"[{safe_thread_id}] AIMessageChunk is raw message tokens, "
                f"content_len={content_len}"
            )
            # Log finish_reason for debugging
            if event_stream_message.get("finish_reason"):
                logger.info(
                    f"[{safe_thread_id}] ✅ Including finish_reason in "
                    f"message_chunk event: "
                    f"{event_stream_message.get('finish_reason')}, "
                    f"message_id: {event_stream_message.get('id')}, "
                    f"agent: {event_stream_message.get('agent')}"
                )
            # NOTE: Don't add finish_reason to all chunks - only include it
            # when it's actually present in the message metadata (final chunk).
            # The frontend will set isStreaming=false when it receives ANY
            # chunk with finish_reason.
            yield _make_event("message_chunk", event_stream_message)


async def _stream_graph_events(
    graph_instance, workflow_input, workflow_config, thread_id
):
    """Stream events from the graph using latest LangGraph features.
    
    Features:
    - messages: Streams LangChain messages (agent responses, tool calls)
    - updates: Streams state updates by node (plan updates, observations)
    - debug: Streams structured debug events for server-side observability
    """
    safe_thread_id = sanitize_thread_id(thread_id)
    logger.debug(
        f"[{safe_thread_id}] Starting graph event stream with "
        f"latest LangGraph features"
    )
    try:
        event_count = 0
        debug_event_count = 0
        
        # Use latest LangGraph streaming with debug mode for observability
        # debug events processed server-side only, not streamed to client
        async for agent, stream_type, event_data in graph_instance.astream(
            workflow_input,
            config=workflow_config,
            stream_mode=["messages", "updates", "debug"],  # Added debug mode
            subgraphs=True,
            debug=False,  # Set to True for verbose debug output
        ):
            event_count += 1
            safe_agent = sanitize_agent_name(agent)
            
            # Process debug events for server-side observability
            if stream_type == "debug":
                debug_event_count += 1
                if isinstance(event_data, dict):
                    event_type = event_data.get("type", "unknown")
                    step = event_data.get("step", 0)
                    timestamp = event_data.get("timestamp", "")
                    
                    if event_type == "task":
                        # Node task started
                        payload = event_data.get("payload", {})
                        task_name = payload.get("name", safe_agent)
                        task_id = payload.get("id", "unknown")
                        logger.info(
                            f"[{safe_thread_id}] 🔵 Task started: {task_name} "
                            f"(id={task_id}, step={step})"
                        )
                    elif event_type == "task_result":
                        # Node task completed
                        payload = event_data.get("payload", {})
                        task_name = payload.get("name", safe_agent)
                        task_id = payload.get("id", "unknown")
                        error = payload.get("error")
                        if error:
                            logger.error(
                                f"[{safe_thread_id}] ❌ Task failed: {task_name} "
                                f"(id={task_id}, step={step}): {error}"
                            )
                        else:
                            logger.info(
                                f"[{safe_thread_id}] ✅ Task completed: {task_name} "
                                f"(id={task_id}, step={step})"
                            )
                    elif event_type == "checkpoint":
                        # State checkpoint created
                        logger.debug(
                            f"[{safe_thread_id}] 💾 Checkpoint created "
                            f"(step={step}, timestamp={timestamp})"
                        )
                
                # Debug events are not streamed to client (too verbose)
                continue
            
            # Process messages and updates for client streaming
            logger.debug(
                f"[{safe_thread_id}] Graph event #{event_count} received "
                f"from agent: {safe_agent}, type: {stream_type}"
            )
            
            if stream_type == "messages":
                # Process message chunks (agent responses, tool calls)
                if isinstance(event_data, (list, tuple)) and len(event_data) > 0:
                    message_chunk, message_metadata = (
                        event_data[0], 
                        event_data[1] if len(event_data) > 1 else {}
                    )
                    async for event in _process_message_chunk(
                        message_chunk, message_metadata, thread_id, agent
                    ):
                        yield event
            
            elif stream_type == "updates":
                # Process state updates (plan updates, observations)
                if isinstance(event_data, dict):
                    # Check for interrupts first
                    if "__interrupt__" in event_data:
                        interrupt_data = event_data['__interrupt__']
                        ns_value = (
                            getattr(interrupt_data[0], 'ns', 'unknown')
                            if isinstance(interrupt_data, (list, tuple))
                            and len(interrupt_data) > 0
                            else 'unknown'
                        )
                        value_len = (
                            len(getattr(interrupt_data[0], 'value', ''))
                            if isinstance(interrupt_data, (list, tuple))
                            and len(interrupt_data) > 0
                            and hasattr(interrupt_data[0], 'value')
                            and hasattr(interrupt_data[0].value, '__len__')
                            else 'unknown'
                        )
                        logger.debug(
                            f"[{safe_thread_id}] Processing interrupt event: "
                            f"ns={ns_value}, value_len={value_len}"
                        )
                        yield _create_interrupt_event(thread_id, event_data)
                    
                    # Process node-specific state updates
                    # With stream_mode=["messages", "updates"], updates come as
                    # dicts keyed by node name
                    for node_name, node_update in event_data.items():
                        if (
                            not isinstance(node_update, dict)
                            or node_name == "__interrupt__"
                        ):
                            continue
                        
                        # Stream plan updates
                        if "current_plan" in node_update:
                            current_plan = node_update.get("current_plan")
                            if current_plan:
                                # Extract plan information
                                plan_data = {}
                                if hasattr(current_plan, 'title'):
                                    plan_data["title"] = current_plan.title
                                if hasattr(current_plan, 'steps'):
                                    plan_data["steps"] = [
                                        {
                                            "title": step.title,
                                            "description": step.description,
                                            "step_type": (
                                                step.step_type.value
                                                if hasattr(
                                                    step.step_type, 'value'
                                                )
                                                else str(step.step_type)
                                            ) if hasattr(
                                                step, 'step_type'
                                            ) else None,
                                            "execution_res": (
                                                step.execution_res
                                                if hasattr(
                                                    step, 'execution_res'
                                                ) else None
                                            ),
                                        }
                                        for step in current_plan.steps
                                    ] if current_plan.steps else []
                                
                                # Stream plan update event
                                logger.info(
                                    f"[{safe_thread_id}] Streaming plan update "
                                    f"from {node_name}: "
                                    f"{len(plan_data.get('steps', []))} steps"
                                )
                                yield _make_event(
                                    "plan_update",
                                    {
                                        "thread_id": thread_id,
                                        "agent": node_name,
                                        "role": "assistant",
                                        "plan": plan_data,
                                    }
                                )
                        
                        # Stream step execution updates
                        if "observations" in node_update:
                            observations = node_update.get("observations", [])
                            if observations:
                                # Get the latest observation (current step result)
                                latest_observation = (
                                    observations[-1] if observations else ""
                                )
                                logger.info(
                                    f"[{safe_thread_id}] Streaming step "
                                    f"execution update from {node_name}: "
                                    f"{len(latest_observation)} chars"
                                )
                                yield _make_event(
                                    "step_update",
                                    {
                                        "thread_id": thread_id,
                                        "agent": node_name,
                                        "role": "assistant",
                                        "observation": latest_observation,
                                        "step_index": len(observations) - 1,
                                    }
                                )
                        
                        # Stream messages from state updates
                        # (e.g., reporter's final report)
                        # NOTE: For reporter messages, we DON'T stream from
                        # state updates because they should already be streamed
                        # in the "messages" stream. Streaming here would create
                        # a duplicate message with a different ID, causing the
                        # frontend to not recognize the finish_reason properly.
                        # Only stream non-reporter messages from state updates.
                        if "messages" in node_update and node_name != "reporter":
                            messages = node_update.get("messages", [])
                            if messages:
                                # Get the latest message
                                for msg in messages:
                                    if (
                                        isinstance(msg, AIMessage)
                                        and msg.name == node_name
                                    ):
                                        logger.debug(
                                            f"[{safe_thread_id}] "
                                            f"Streaming {node_name} message "
                                            f"from state update: "
                                            f"{len(msg.content)} chars, "
                                            f"id: {msg.id}"
                                        )
                                        # Ensure finish_reason is set
                                        if not msg.response_metadata:
                                            msg.response_metadata = {}
                                        if (
                                            "finish_reason"
                                            not in msg.response_metadata
                                        ):
                                            msg.response_metadata[
                                                "finish_reason"
                                            ] = "stop"
                                        msg_metadata = {
                                            "langgraph_node": node_name,
                                            "finish_reason": "stop"
                                        }
                                        async for event in _process_message_chunk(
                                            msg,
                                            msg_metadata,
                                            thread_id,
                                            (node_name,),
                                        ):
                                            yield event
                                        break
                    
                    logger.debug(
                        f"[{safe_thread_id}] Processed state update from "
                        f"{safe_agent}"
                    )
        
        logger.info(
            f"[{safe_thread_id}] ✅ Streaming completed: {event_count} events, "
            f"{debug_event_count} debug events processed"
        )
    except Exception as e:
        logger.error(
            f"[{safe_thread_id}] ❌ Error in graph event stream: {e}",
            exc_info=True
        )
        yield _make_event(
            "error",
            {
                "thread_id": thread_id,
                "error": f"Streaming error: {str(e)}",
            }
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
    safe_feedback = (
        sanitize_log_input(interrupt_feedback) if interrupt_feedback else ""
    )
    logger.debug(
        f"[{safe_thread_id}] _astream_workflow_generator starting: "
        f"messages_count={len(messages)}, "
        f"auto_accepted_plan={auto_accepted_plan}, "
        f"interrupt_feedback={safe_feedback}, "
        f"interrupt_before_tools={interrupt_before_tools}"
    )

    # Process initial messages
    logger.debug(
        f"[{safe_thread_id}] Processing {len(messages)} initial messages"
    )
    for message in messages:
        if isinstance(message, dict) and "content" in message:
            safe_content = sanitize_user_content(message.get('content', ''))
            logger.debug(
                f"[{safe_thread_id}] Sending initial message to client: "
                f"{safe_content}"
            )
            _process_initial_messages(message, thread_id)

    logger.debug(
        f"[{safe_thread_id}] Reconstructing clarification history"
    )
    clarification_history = reconstruct_clarification_history(messages)

    logger.debug(
        f"[{safe_thread_id}] Building clarified topic from history"
    )
    clarified_topic, clarification_history = (
        build_clarified_topic_from_history(clarification_history)
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
        logger.debug(
            f"[{safe_thread_id}] Creating resume command with "
            f"interrupt_feedback: {safe_feedback}"
        )
        resume_msg = f"[{interrupt_feedback}]"
        if messages:
            resume_msg += f" {messages[-1]['content']}"
        workflow_input = Command(resume=resume_msg)  # type: ignore

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
            logger.info(
                f"[{safe_thread_id}] Starting async postgres checkpointer"
            )
            logger.debug(
                f"[{safe_thread_id}] Setting up PostgreSQL connection pool"
            )
            async with AsyncConnectionPool(
                checkpoint_url, kwargs=connection_kwargs
            ) as conn:
                logger.debug(
                    f"[{safe_thread_id}] Initializing AsyncPostgresSaver"
                )
                checkpointer = AsyncPostgresSaver(conn)  # type: ignore
                await checkpointer.setup()
                logger.debug(
                    f"[{safe_thread_id}] Attaching checkpointer to graph"
                )
                graph.checkpointer = checkpointer
                graph.store = in_memory_store
                logger.debug(
                    f"[{safe_thread_id}] Starting to stream graph events"
                )
                async for event in _stream_graph_events(
                    graph, workflow_input, workflow_config, thread_id
                ):
                    yield event
                logger.debug(
                    f"[{safe_thread_id}] Graph event streaming completed"
                )

        if checkpoint_url.startswith("mongodb://"):
            logger.info(
                f"[{safe_thread_id}] Starting async mongodb checkpointer"
            )
            logger.debug(
                f"[{safe_thread_id}] Setting up MongoDB connection"
            )
            async with AsyncMongoDBSaver.from_conn_string(
                checkpoint_url
            ) as mongo_checkpointer:  # type: ignore[assignment]
                # Type ignore: MongoDB checkpointer is compatible
                # with graph.checkpointer interface
                logger.debug(
                    f"[{safe_thread_id}] Attaching MongoDB checkpointer "
                    f"to graph"
                )
                # Type ignore: MongoDB checkpointer compatible interface
                # type: ignore[assignment]
                graph.checkpointer = mongo_checkpointer
                graph.store = in_memory_store
                logger.debug(
                    f"[{safe_thread_id}] Starting to stream graph events"
                )
                async for event in _stream_graph_events(
                    graph, workflow_input, workflow_config, thread_id
                ):
                    yield event
                logger.debug(
                    f"[{safe_thread_id}] Graph event streaming completed"
                )
    else:
        logger.debug(
            f"[{safe_thread_id}] No checkpointer configured, "
            f"using in-memory graph"
        )
        # Use graph without MongoDB checkpointer
        logger.debug(
            f"[{safe_thread_id}] Starting to stream graph events"
        )
        async for event in _stream_graph_events(
            graph, workflow_input, workflow_config, thread_id
        ):
            yield event
        logger.debug(f"[{safe_thread_id}] Graph event streaming completed")


def _make_event(event_type: str, data: dict[str, Any]):
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
        error_data = json.dumps(
            {"error": "Serialization failed"}, ensure_ascii=False
        )
        return f"event: error\ndata: {error_data}\n\n"


@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """Convert text to speech using volcengine TTS API."""
    app_id = get_str_env("VOLCENGINE_TTS_APPID", "")
    if not app_id:
        raise HTTPException(
            status_code=400, detail="VOLCENGINE_TTS_APPID is not set"
        )
    access_token = get_str_env("VOLCENGINE_TTS_ACCESS_TOKEN", "")
    if not access_token:
        raise HTTPException(
            status_code=400, detail="VOLCENGINE_TTS_ACCESS_TOKEN is not set"
        )

    try:
        cluster = get_str_env("VOLCENGINE_TTS_CLUSTER", "volcano_tts")
        voice_type = get_str_env(
            "VOLCENGINE_TTS_VOICE_TYPE", "BV700_V2_streaming"
        )

        tts_client = VolcengineTTS(
            appid=app_id,
            access_token=access_token,
            cluster=cluster,
            voice_type=voice_type,
        )
        # Call the TTS API with defaults for optional parameters
        result = tts_client.text_to_speech(
            text=request.text[:1024],
            encoding=request.encoding or "mp3",
            speed_ratio=request.speed_ratio or 1.0,
            volume_ratio=request.volume_ratio or 1.0,
            pitch_ratio=request.pitch_ratio or 1.0,
            text_type=request.text_type or "plain",
            with_frontend=request.with_frontend or 1,
            frontend_type=request.frontend_type or "unitTson",
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
        raise HTTPException(
            status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL
        )


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
        raise HTTPException(
            status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL
        )


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
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "presentationml.presentation"
            ),
        )
    except Exception as e:
        logger.exception(f"Error occurred during ppt generation: {str(e)}")
        raise HTTPException(
            status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL
        )


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
        raise HTTPException(
            status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL
        )


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
        raise HTTPException(
            status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL
        )


@app.post(
    "/api/mcp/server/metadata", response_model=MCPServerMetadataResponse
)
async def mcp_server_metadata(request: MCPServerMetadataRequest):
    """Get information about an MCP server."""
    # Check if MCP server configuration is enabled
    if not get_bool_env("ENABLE_MCP_SERVER_CONFIGURATION", False):
        raise HTTPException(
            status_code=403,
            detail=(
                "MCP server configuration is disabled. "
                "Set ENABLE_MCP_SERVER_CONFIGURATION=true to enable "
                "MCP features."
            ),
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
        raise HTTPException(
            status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL
        )


@app.get("/api/rag/config", response_model=RAGConfigResponse)
async def rag_config():
    """Get the config of the RAG."""
    return RAGConfigResponse(provider=SELECTED_RAG_PROVIDER)


@app.get("/api/rag/resources", response_model=RAGResourcesResponse)
async def rag_resources(request: Annotated[RAGResourceRequest, Query()]):
    """Get the resources of the RAG."""
    retriever = build_retriever()
    if retriever:
        return RAGResourcesResponse(
            resources=retriever.list_resources(request.query)
        )
    return RAGResourcesResponse(resources=[])


@app.get("/api/config", response_model=ConfigResponse)
async def config():
    """Get the config of the server."""
    return ConfigResponse(
        rag=RAGConfigResponse(provider=SELECTED_RAG_PROVIDER),
        models=get_configured_llm_models(),
    )

# Project Management Agent API endpoints
# NOTE: Legacy PostgreSQL REST endpoints removed - all PM operations
# now go through /api/pm/chat/stream
# This endpoint uses PM Providers (OpenProject, JIRA, etc.)
# instead of local database


# PM REST endpoints for UI data fetching
@app.get("/api/pm/projects")
async def pm_list_projects(request: Request):
    """List all projects from all active PM providers"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            handler = PMHandler.from_db_session(db)
            return await handler.list_all_projects()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/projects/{project_id}/tasks")
async def pm_list_tasks(request: Request, project_id: str):
    """List all tasks for a project"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            # Check if project_id has provider prefix
            if ":" not in project_id:
                # Fallback: use global flow_manager if no provider_id prefix
                from src.conversation.flow_manager import (
                    ConversationFlowManager
                )
                global flow_manager
                if flow_manager is None:
                    flow_manager = ConversationFlowManager(db_session=db)
                fm = flow_manager
                
                if not fm.pm_provider:
                    raise HTTPException(
                        status_code=503, detail="PM Provider not configured"
                    )
                
                tasks = await fm.pm_provider.list_tasks(
                    project_id=project_id
                )
                # Continue with assignee map logic below
                assignee_map = {}
                for task in tasks:
                    if (task.assignee_id and
                            task.assignee_id not in assignee_map):
                        try:
                            user = await fm.pm_provider.get_user(
                                task.assignee_id
                            )
                            if user:
                                assignee_map[task.assignee_id] = user.name
                        except Exception:
                            pass
                
                return [
                    {
                        "id": str(t.id),
                        "title": t.title,
                        "description": t.description,
                        "status": (
                            t.status.value
                            if hasattr(t.status, 'value')
                            else str(t.status)
                        ),
                        "priority": (
                            t.priority.value
                            if hasattr(t.priority, 'value')
                            else str(t.priority)
                        ),
                        "estimated_hours": t.estimated_hours,
                        "start_date": (
                            t.start_date.isoformat() if t.start_date else None
                        ),
                        "due_date": (
                            t.due_date.isoformat() if t.due_date else None
                        ),
                        "assigned_to": (
                            assignee_map.get(t.assignee_id)
                            if t.assignee_id
                            else None
                        ),
                        "assignee_id": str(t.assignee_id) if t.assignee_id else None,
                    }
                    for t in tasks
                ]
            
            # Use PMHandler for provider-prefixed project IDs
            handler = PMHandler.from_db_session(db)
            tasks = await handler.list_project_tasks(project_id)
            return tasks
        finally:
            db.close()
    except ValueError as ve:
        # Handle ValueError from PMHandler and convert to HTTPException
        error_msg = str(ve)
        # Extract status code if present in format "(410) message"
        import re
        status_match = re.match(r'\((\d{3})\)\s*(.+)', error_msg)
        if status_match:
            status_code = int(status_match.group(1))
            detail = status_match.group(2)
            raise HTTPException(status_code=status_code, detail=detail)
        else:
            # Check for specific error patterns
            if "Invalid provider ID format" in error_msg:
                raise HTTPException(status_code=400, detail=error_msg)
            elif "Provider not found" in error_msg:
                raise HTTPException(status_code=404, detail=error_msg)
            elif "not yet implemented" in error_msg:
                raise HTTPException(status_code=501, detail=error_msg)
            else:
                raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        # Re-raise HTTPExceptions as-is (preserve status codes)
        raise
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/tasks/my")
async def pm_list_my_tasks(request: Request):
    """List tasks assigned to current user across all active PM providers"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            handler = PMHandler.from_db_session(db)
            return await handler.list_my_tasks()
        finally:
            db.close()
    except HTTPException:
        # Re-raise HTTPExceptions as-is (preserve status codes)
        raise
    except Exception as e:
        logger.error(f"Failed to list my tasks: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/tasks/all")
async def pm_list_all_tasks(request: Request):
    """List all tasks across all projects from all active PM providers"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            handler = PMHandler.from_db_session(db)
            return await handler.list_all_tasks()
        finally:
            db.close()
    except HTTPException:
        # Re-raise HTTPExceptions as-is (preserve status codes)
        raise
    except Exception as e:
        logger.error(f"Failed to list all tasks: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/pm/tasks/{task_id}")
async def pm_update_task(request: Request, task_id: str, project_id: str = Query(..., description="Project ID in format 'provider_id:project_key'")):
    """Update a task"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        updates = await request.json()
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            handler = PMHandler.from_db_session(db)
            provider = handler._get_provider_for_project(project_id)
            
            logger.info(f"Updating task {task_id} in project {project_id} with updates: {updates}")
            
            # Update the task using the provider
            updated_task = await provider.update_task(task_id, updates)
            
            logger.info(f"Task {task_id} updated successfully: {updated_task.title}")
            
            # Get project name for response
            actual_project_id = project_id.split(":")[-1]
            project = await provider.get_project(actual_project_id)
            project_name = project.name if project else "Unknown"
            
            # Convert to dict format
            result = handler._task_to_dict(updated_task, project_name)
            logger.info(f"Returning updated task data: {result}")
            return result
        finally:
            db.close()
    except ValueError as ve:
        error_msg = str(ve)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        elif "OpenProject API error (422)" in error_msg:
            # Preserve 422 status code for OpenProject validation errors
            # Extract the actual error message after the status code
            detail = error_msg.replace("OpenProject API error (422): ", "")
            raise HTTPException(status_code=422, detail=detail)
        elif "OpenProject API error" in error_msg:
            # Extract status code from error message if present
            import re
            status_match = re.search(r'\((\d+)\)', error_msg)
            status_code = int(status_match.group(1)) if status_match else 400
            detail = error_msg.split(": ", 1)[1] if ": " in error_msg else error_msg
            raise HTTPException(status_code=status_code, detail=detail)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        # Re-raise HTTPExceptions as-is (preserve status codes)
        raise
    except Exception as e:
        logger.error(f"Failed to update task: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/projects/{project_id}/users")
async def pm_list_users(request: Request, project_id: str):
    """List all users for a project"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            handler = PMHandler.from_db_session(db)
            provider_instance = handler._get_provider_for_project(project_id)

            actual_project_id = (
                project_id.split(":", 1)[1]
                if ":" in project_id
                else project_id
            )

            provider_type = getattr(
                getattr(provider_instance, "config", None),
                "provider_type",
                provider_instance.__class__.__name__
            )

            try:
                user_objs = await provider_instance.list_users(
                    project_id=actual_project_id
                )
            except NotImplementedError:
                raise HTTPException(
                    status_code=501,
                    detail=f"User listing not yet implemented for {provider_type}"
                )
            except ValueError as ve:
                error_msg = str(ve)
                if "JIRA requires" in error_msg or "username" in error_msg.lower() or "api_token" in error_msg.lower():
                    logger.warning(
                        "[pm_list_users] Provider authentication issue, returning empty list. Error: %s",
                        error_msg
                    )
                    return []
                raise HTTPException(status_code=400, detail=error_msg)
            except Exception as e:
                error_msg = str(e)
                if "JIRA requires" in error_msg or "username" in error_msg.lower():
                    logger.warning(
                        "[pm_list_users] Provider configuration issue, returning empty list. Error: %s",
                        error_msg
                    )
                    return []
                logger.error(f"Failed to list users: {e}")
                import traceback
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=error_msg)

            return [
                {
                    "id": str(u.id),
                    "name": u.name,
                    "email": u.email or "",
                    "username": u.username or "",
                    "avatar_url": u.avatar_url or "",
                }
                for u in user_objs
            ]
        finally:
            db.close()
    except ValueError as ve:
        error_msg = str(ve)
        # For JIRA username/auth issues, return empty list instead of error
        if "JIRA requires email" in error_msg or "JIRA requires" in error_msg or "username" in error_msg.lower() or "api_token" in error_msg.lower():
            logger.warning(f"[pm_list_users] Outer handler: JIRA authentication issue, returning empty user list. Error: {error_msg}")
            return []
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        # For JIRA username/auth issues, return empty list instead of error
        if "JIRA requires" in error_msg or "username" in error_msg.lower():
            logger.warning(f"[pm_list_users] Outer handler: JIRA configuration issue, returning empty user list. Error: {error_msg}")
            return []
        logger.error(f"Failed to list users: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/projects/{project_id}/sprints")
async def pm_list_sprints(
    request: Request, 
    project_id: str,
    state: Optional[str] = None
):
    """List all sprints for a project"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            # Check if project_id has provider prefix
            if ":" not in project_id:
                # Fallback: use global flow_manager if no provider_id prefix
                from src.conversation.flow_manager import ConversationFlowManager
                
                global flow_manager
                if flow_manager is None:
                    flow_manager = ConversationFlowManager(db_session=db)
                fm = flow_manager
                
                if not fm.pm_provider:
                    raise HTTPException(
                        status_code=503, detail="PM Provider not configured"
                    )
                
                sprints = await fm.pm_provider.list_sprints(project_id=project_id)
                
                return [
                    {
                        "id": str(s.id),
                        "name": s.name,
                        "start_date": (
                            s.start_date.isoformat() if s.start_date else None
                        ),
                        "end_date": (
                            s.end_date.isoformat() if s.end_date else None
                        ),
                        "status": (
                            s.status.value
                            if hasattr(s.status, 'value')
                            else str(s.status)
                        ),
                    }
                    for s in sprints
                ]
            
            # Use PMHandler for provider-prefixed project IDs
            handler = PMHandler.from_db_session(db)
            return await handler.list_project_sprints(project_id, state=state)
        finally:
            db.close()
    except ValueError as ve:
        # Handle ValueError from PMHandler and convert to HTTPException
        error_msg = str(ve)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        # Re-raise HTTPExceptions as-is (preserve status codes)
        raise
    except Exception as e:
        logger.error(f"Failed to list sprints: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/projects/{project_id}/epics")
async def pm_list_epics(request: Request, project_id: str):
    """List all epics for a project"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            handler = PMHandler.from_db_session(db)
            return await handler.list_project_epics(project_id)
        finally:
            db.close()
    except ValueError as ve:
        error_msg = str(ve)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        elif "not yet implemented" in error_msg:
            raise HTTPException(status_code=501, detail=error_msg)
        else:
            raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list epics: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pm/projects/{project_id}/epics")
async def pm_create_epic(request: Request, project_id: str):
    """Create a new epic for a project"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        epic_data = await request.json()
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            handler = PMHandler.from_db_session(db)
            return await handler.create_project_epic(project_id, epic_data)
        finally:
            db.close()
    except ValueError as ve:
        error_msg = str(ve)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        elif "not yet implemented" in error_msg:
            raise HTTPException(status_code=501, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create epic: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/pm/projects/{project_id}/epics/{epic_id}")
async def pm_update_epic(request: Request, project_id: str, epic_id: str):
    """Update an epic for a project"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        updates = await request.json()
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            handler = PMHandler.from_db_session(db)
            return await handler.update_project_epic(project_id, epic_id, updates)
        finally:
            db.close()
    except ValueError as ve:
        error_msg = str(ve)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        elif "not yet implemented" in error_msg:
            raise HTTPException(status_code=501, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update epic: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pm/projects/{project_id}/tasks/{task_id}/assign-epic")
async def pm_assign_task_to_epic(request: Request, project_id: str, task_id: str):
    """Assign a task to an epic"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        epic_data = await request.json()
        epic_id = epic_data.get("epic_id")
        if not epic_id:
            raise HTTPException(status_code=400, detail="epic_id is required")
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            handler = PMHandler.from_db_session(db)
            return await handler.assign_task_to_epic(project_id, task_id, epic_id)
        finally:
            db.close()
    except ValueError as ve:
        error_msg = str(ve)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign task to epic: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pm/projects/{project_id}/tasks/{task_id}/remove-epic")
async def pm_remove_task_from_epic(request: Request, project_id: str, task_id: str):
    """Remove a task from its epic"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            handler = PMHandler.from_db_session(db)
            return await handler.remove_task_from_epic(project_id, task_id)
        finally:
            db.close()
    except ValueError as ve:
        error_msg = str(ve)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove task from epic: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pm/projects/{project_id}/tasks/{task_id}/assign-sprint")
async def pm_assign_task_to_sprint(request: Request, project_id: str, task_id: str):
    """Assign a task to a sprint"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        sprint_data = await request.json()
        sprint_id = sprint_data.get("sprint_id")
        if not sprint_id:
            raise HTTPException(status_code=400, detail="sprint_id is required")
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            handler = PMHandler.from_db_session(db)
            return await handler.assign_task_to_sprint(project_id, task_id, sprint_id)
        finally:
            db.close()
    except ValueError as ve:
        error_msg = str(ve)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign task to sprint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pm/projects/{project_id}/tasks/{task_id}/move-to-backlog")
async def pm_move_task_to_backlog(request: Request, project_id: str, task_id: str):
    """Move a task to the backlog"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            handler = PMHandler.from_db_session(db)
            return await handler.move_task_to_backlog(project_id, task_id)
        finally:
            db.close()
    except ValueError as ve:
        error_msg = str(ve)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to move task to backlog: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/pm/projects/{project_id}/epics/{epic_id}")
async def pm_delete_epic(request: Request, project_id: str, epic_id: str):
    """Delete an epic for a project"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            handler = PMHandler.from_db_session(db)
            success = await handler.delete_project_epic(project_id, epic_id)
            if success:
                return {"success": True}
            else:
                raise HTTPException(status_code=404, detail="Epic not found")
        finally:
            db.close()
    except ValueError as ve:
        error_msg = str(ve)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        elif "not yet implemented" in error_msg:
            raise HTTPException(status_code=501, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete epic: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/projects/{project_id}/labels")
async def pm_list_labels(request: Request, project_id: str):
    """List all labels for a project"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            handler = PMHandler.from_db_session(db)
            return await handler.list_project_labels(project_id)
        finally:
            db.close()
    except ValueError as ve:
        error_msg = str(ve)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        elif "not yet implemented" in error_msg:
            raise HTTPException(status_code=501, detail=error_msg)
        else:
            raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list labels: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/projects/{project_id}/statuses")
async def pm_list_statuses(
    request: Request,
    project_id: str,
    entity_type: str = "task"
):
    """
    Get list of available statuses for an entity type in a project.
    
    This is used by UI/UX to create status columns in Kanban boards and combo boxes.
    
    Returns status objects with id, name, color, etc.
    """
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            handler = PMHandler.from_db_session(db)
            logger.info(f"[pm_list_statuses] project_id={project_id}")
            statuses = await handler.list_project_statuses(project_id, entity_type)
            return {"statuses": statuses, "entity_type": entity_type}
        finally:
            db.close()
    except ValueError as ve:
        error_msg = str(ve)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        elif "not yet implemented" in error_msg:
            raise HTTPException(status_code=501, detail=error_msg)
        else:
            raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list statuses: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/projects/{project_id}/priorities")
async def pm_list_priorities(
    request: Request,
    project_id: str
):
    """
    Get list of available priorities for a project.
    
    This is used by UI/UX to populate priority dropdowns/selectors.
    
    Returns priority objects with id, name, color, etc.
    """
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            handler = PMHandler.from_db_session(db)
            logger.info(f"Listing priorities for project_id: {project_id}")
            priorities = await handler.list_project_priorities(project_id)
            logger.info(f"Found {len(priorities)} priorities for project {project_id}")
            return {"priorities": priorities}
        finally:
            db.close()
    except ValueError as ve:
        error_msg = str(ve)
        logger.error(f"ValueError listing priorities for {project_id}: {error_msg}")
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        elif "not yet implemented" in error_msg:
            raise HTTPException(status_code=501, detail=error_msg)
        else:
            raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list priorities for {project_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# PM Chat endpoint
@app.post("/api/pm/chat/stream")
async def pm_chat_stream(request: Request):
    """Stream chat responses for Project Management tasks"""
    try:
        from src.conversation.flow_manager import ConversationFlowManager
        from database.connection import get_db_session
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
                logger.info(
                    "Created global ConversationFlowManager singleton"
                )
            fm = flow_manager
                
            async def generate_stream() -> AsyncIterator[str]:
                """Generate SSE stream of chat responses with progress."""
                api_start = time.time()
                logger.info("[PM-CHAT-TIMING] generate_stream started")
                    
                try:
                    # Option 2: Route everything to DeerFlow (skip PM plan generation)
                    # This avoids project ID errors for research queries
                    # All queries go through DeerFlow agents which decide what tools to use
                    needs_research = True  # Always route to DeerFlow with Option 2
                    
                    logger.info(
                        f"[PM-CHAT-TIMING] Routing to DeerFlow (Option 2) - "
                        f"{time.time() - api_start:.2f}s"
                    )
                        
                    # Route all queries to DeerFlow
                    if needs_research:
                        initial_chunk = {
                            "id": str(uuid.uuid4()),
                            "thread_id": thread_id,
                            "agent": "coordinator",
                            "role": "assistant",
                            "content": (
                                "🦌 **Starting DeerFlow research...**\n\n"
                            ),
                            "finish_reason": None
                        }
                        yield "event: message_chunk\n"
                        yield f"data: {json.dumps(initial_chunk)}\n\n"
                            
                        try:
                            # Ensure PM handler is set for tools before agents run
                            if fm.pm_handler:
                                from src.tools.pm_tools import set_pm_handler
                                set_pm_handler(fm.pm_handler)
                                logger.info(
                                    "[PM-CHAT-TIMING] PM handler set for "
                                    "DeerFlow agents"
                                )
                            
                            # Use original message for research query (Option 2: agents decide what to do)
                            research_query = user_message
                                
                            research_start = time.time()
                            logger.info(
                                f"[PM-CHAT-TIMING] Starting DeerFlow "
                                f"research: {time.time() - api_start:.2f}s"
                            )
                            final_research_state = None
                                
                            # Use _astream_workflow_generator to get properly
                            # formatted research events
                            from src.config.report_style import ReportStyle
                                
                            async for event in _astream_workflow_generator(
                                messages=[
                                    {"role": "user", "content": research_query}
                                ],
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
                            final_research_state = {
                                "final_report": "Research completed"
                            }
                                
                            # Store research result
                            if final_research_state:
                                from src.conversation.flow_manager import (
                                    ConversationContext,
                                    FlowState,
                                    IntentType,
                                )
                                from datetime import datetime
                                    
                                if thread_id not in fm.contexts:
                                    fm.contexts[thread_id] = (
                                        ConversationContext(
                                            session_id=thread_id,
                                            current_state=(
                                                FlowState.INTENT_DETECTION
                                            ),
                                            intent=IntentType.UNKNOWN,
                                            gathered_data={},
                                            required_fields=[],
                                            conversation_history=[],
                                            created_at=datetime.now(),
                                            updated_at=datetime.now()
                                        )
                                    )
                                    
                                context = fm.contexts[thread_id]
                                context.gathered_data['research_context'] = (
                                    "Research completed"
                                )
                                context.gathered_data[
                                    'research_already_done'
                                ] = True
                                logger.info(
                                    f"Stored research result in context for "
                                    f"session {thread_id}"
                                )

                            research_duration = time.time() - research_start
                            logger.info(
                                f"[PM-CHAT-TIMING] DeerFlow research "
                                f"completed: {research_duration:.2f}s"
                            )
                            
                        except Exception as research_error:
                            logger.error(
                                f"DeerFlow streaming failed: {research_error}"
                            )
                            import traceback
                            logger.error(traceback.format_exc())
                        
                        # Option 2: All queries handled by DeerFlow, skip process_message
                        # This avoids project ID errors for research queries
                        logger.info(
                            "[PM-CHAT-TIMING] Skipping process_message - "
                            "DeerFlow handled the query"
                        )
                        # DeerFlow already streamed all responses, so we're done
                        
                    logger.info(
                        f"[PM-CHAT-TIMING] Total response time: "
                        f"{time.time() - api_start:.2f}s"
                    )
                    
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


# PM Provider Management Endpoints

@app.get("/api/pm/providers")
async def pm_list_providers():
    """List all configured PM providers"""
    try:
        from database.connection import get_db_session
        from database.orm_models import PMProviderConnection
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            providers = db.query(PMProviderConnection).filter(
                PMProviderConnection.is_active.is_(True)
            ).all()
            return [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "provider_type": p.provider_type,
                    "base_url": p.base_url,
                    "username": p.username,
                    "organization_id": p.organization_id,
                    "workspace_id": p.workspace_id,
                }
                for p in providers
            ]
        finally:
            db.close()
    except Exception as e:
        # Log the full error for debugging
        error_msg = str(e)
        logger.error(f"Failed to list providers: {error_msg}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Return proper error response so the issue can be identified
        # and fixed immediately
        if "connection" in error_msg.lower() or "Connection refused" in error_msg:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Database connection unavailable. "
                    "Please ensure PostgreSQL is running and configured. "
                    f"Error: {error_msg}"
                )
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list providers: {error_msg}"
            )


@app.post("/api/pm/providers/import-projects")
async def pm_import_projects(request: ProjectImportRequest):
    """Save provider configuration and import projects"""
    try:
        from database.connection import get_db_session
        from database.orm_models import PMProviderConnection
        from src.pm_providers.factory import create_pm_provider
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            # Create provider config
            provider = PMProviderConnection(
                name=f"{request.provider_type} - {request.base_url}",
                provider_type=request.provider_type,
                base_url=request.base_url,
                api_key=request.api_key,
                api_token=request.api_token,
                username=request.username,
                organization_id=request.organization_id,
                workspace_id=request.workspace_id,
                is_active=True
            )
            db.add(provider)
            db.commit()
            db.refresh(provider)
            
            # Create provider instance and import projects
            provider_instance = create_pm_provider(
                provider_type=request.provider_type,
                base_url=request.base_url,
                api_key=request.api_key,
                api_token=request.api_token,
                username=request.username,
                organization_id=request.organization_id,
                workspace_id=request.workspace_id,
            )
            
            try:
                projects = await provider_instance.list_projects()
            except Exception as api_error:
                error_msg = str(api_error)
                # Handle specific HTTP errors
                if "401" in error_msg or "Unauthorized" in error_msg:
                    raise HTTPException(
                        status_code=401,
                        detail=(
                            "Authentication failed. "
                            "Please check your API key/token."
                        )
                    )
                elif "404" in error_msg or "Not Found" in error_msg:
                    raise HTTPException(
                        status_code=404,
                        detail=(
                            "Provider API endpoint not found. "
                            "Please check the base URL."
                        )
                    )
                elif (
                    "Connection" in error_msg
                    or "refused" in error_msg.lower()
                ):
                    raise HTTPException(
                        status_code=503,
                        detail=(
                            "Cannot connect to provider. "
                            "Please check if the service is running."
                        )
                    )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to fetch projects: {error_msg}"
                    )
            
            return {
                "success": True,
                "provider_config_id": str(provider.id),
                "total_projects": len(projects),
                "projects": [
                    {
                        "id": str(p.id),
                        "name": p.name,
                        "description": p.description or "",
                        "status": (
                            str(p.status) if hasattr(p, 'status') else None
                        ),
                    }
                    for p in projects
                ],
                "errors": []
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to import projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/providers/types")
async def pm_get_provider_types():
    """Get available provider types"""
    return {
        "types": [
            {"value": "openproject", "label": "OpenProject"},
            {"value": "jira", "label": "JIRA"},
            {"value": "clickup", "label": "ClickUp"},
        ]
    }


@app.get("/api/pm/providers/{provider_id}/projects")
async def pm_get_provider_projects(provider_id: str):
    """Get projects for a specific provider"""
    try:
        from database.connection import get_db_session
        from database.orm_models import PMProviderConnection
        from src.pm_providers.factory import create_pm_provider
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            from uuid import UUID
            try:
                provider_uuid = UUID(provider_id)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid provider ID format"
                )
            
            provider = db.query(PMProviderConnection).filter(
                PMProviderConnection.id == provider_uuid,
                PMProviderConnection.is_active.is_(True)
            ).first()
            
            if not provider:
                raise HTTPException(
                    status_code=404, detail="Provider not found"
                )
            
            # Prepare API key - handle empty strings and None
            api_key_value = None
            if provider.api_key:
                api_key_str = str(provider.api_key).strip()
                api_key_value = api_key_str if api_key_str else None
            
            api_token_value = None
            if provider.api_token:
                api_token_str = str(provider.api_token).strip()
                api_token_value = api_token_str if api_token_str else None
            
            # Log API key status (masked for security)
            has_api_key = bool(api_key_value)
            has_api_token = bool(api_token_value)
            logger.info(
                f"Creating provider instance: type={provider.provider_type}, "
                f"base_url={provider.base_url}, "
                f"has_api_key={has_api_key}, "
                f"has_api_token={has_api_token}, "
                f"username={provider.username}"
            )
            
            # Create provider instance
            provider_instance = create_pm_provider(
                provider_type=str(provider.provider_type),
                base_url=str(provider.base_url),
                api_key=api_key_value,
                api_token=api_token_value,
                username=(
                    str(provider.username).strip()
                    if provider.username
                    else None
                ),
                organization_id=(
                    str(provider.organization_id)
                    if provider.organization_id
                    else None
                ),
                workspace_id=(
                    str(provider.workspace_id)
                    if provider.workspace_id
                    else None
                ),
            )
            
            try:
                projects = await provider_instance.list_projects()
            except Exception as api_error:
                error_msg = str(api_error)
                # Handle specific HTTP errors
                if "401" in error_msg or "Unauthorized" in error_msg:
                    raise HTTPException(
                        status_code=401,
                        detail=(
                            "Authentication failed. "
                            "Please check your API key/token."
                        )
                    )
                elif "404" in error_msg or "Not Found" in error_msg:
                    raise HTTPException(
                        status_code=404,
                        detail=(
                            "Provider API endpoint not found. "
                            "Please check the base URL."
                        )
                    )
                elif (
                    "Connection" in error_msg
                    or "refused" in error_msg.lower()
                ):
                    raise HTTPException(
                        status_code=503,
                        detail=(
                            "Cannot connect to provider. "
                            "Please check if the service is running."
                        )
                    )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to fetch projects: {error_msg}"
                    )
            
            return [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "description": p.description or "",
                    "status": str(p.status) if hasattr(p, 'status') else None,
                }
                for p in projects
            ]
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get provider projects: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/pm/providers/{provider_id}")
async def pm_update_provider(provider_id: str, request: ProviderUpdateRequest):
    """Update a provider configuration"""
    try:
        from database.connection import get_db_session
        from database.orm_models import PMProviderConnection
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            from uuid import UUID
            try:
                provider_uuid = UUID(provider_id)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid provider ID format"
                )
            
            provider = db.query(PMProviderConnection).filter(
                PMProviderConnection.id == provider_uuid
            ).first()
            
            if not provider:
                raise HTTPException(
                    status_code=404, detail="Provider not found"
                )
            
            # Update fields if provided
            update_data = request.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if hasattr(provider, key):
                    # Handle None values - allow setting to None to clear
                    # But skip empty strings (they should be treated as None)
                    if value is not None:
                        # Strip strings and convert empty strings to None
                        if isinstance(value, str):
                            value = value.strip() or None
                        setattr(provider, key, value)
                    elif value is None and key in ['api_key', 'api_token']:
                        # Explicitly allow None for API keys to clear them
                        setattr(provider, key, None)
            
            db.commit()
            db.refresh(provider)
            
            return {
                "id": str(provider.id),
                "name": provider.name,
                "provider_type": provider.provider_type,
                "base_url": provider.base_url,
                "username": provider.username,
                "organization_id": provider.organization_id,
                "workspace_id": provider.workspace_id,
            }
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update provider: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pm/providers/test-connection")
async def pm_test_connection(request: ProjectImportRequest):
    """Test connection to a provider"""
    try:
        from src.pm_providers.factory import create_pm_provider
        
        # Create provider instance
        provider_instance = create_pm_provider(
            provider_type=request.provider_type,
            base_url=request.base_url,
            api_key=request.api_key,
            api_token=request.api_token,
            username=request.username,
            organization_id=request.organization_id,
            workspace_id=request.workspace_id,
        )
        
        # Test by listing projects
        projects = await provider_instance.list_projects()
        
        return {
            "success": True,
            "message": (
                f"Connection successful. "
                f"Found {len(projects)} project(s)."
            ),
        }
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}"
        }


@app.delete("/api/pm/providers/{provider_id}")
async def pm_delete_provider(provider_id: str):
    """Delete (deactivate) a provider"""
    try:
        from database.connection import get_db_session
        from database.orm_models import PMProviderConnection
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            from uuid import UUID
            try:
                provider_uuid = UUID(provider_id)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid provider ID format"
                )
            
            provider = db.query(PMProviderConnection).filter(
                PMProviderConnection.id == provider_uuid
            ).first()
            
            if not provider:
                raise HTTPException(
                    status_code=404, detail="Provider not found"
                )
            
            # Soft delete by deactivating
            provider.is_active = False  # type: ignore
            db.commit()
            
            return {"success": True, "message": "Provider deactivated"}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Analytics Endpoints
# ============================================================================

from src.analytics.service import AnalyticsService
from src.analytics.adapters.pm_adapter import PMProviderAnalyticsAdapter
from database.orm_models import PMProviderConnection
from src.server.pm_handler import PMHandler


def get_analytics_service(project_id: str, db) -> AnalyticsService:
    """
    Get analytics service configured for the project's PM provider.
    
    Args:
        project_id: Project ID (format: "uuid:project_key" or just "project_id")
        db: Database session
    
    Returns:
        AnalyticsService configured with real data adapter
    """
    try:
        # Check if this is the Mock Project - use MockPMProvider
        if project_id.startswith("mock:"):
            logger.info(f"[Analytics] Using MockPMProvider for project: {project_id}")
            from src.pm_providers.mock_provider import MockPMProvider
            from src.pm_providers.models import PMProviderConfig
            
            config = PMProviderConfig(
                provider_type="mock",
                base_url="mock://demo",
                api_key="mock-key"
            )
            mock_provider = MockPMProvider(config)
            adapter = PMProviderAnalyticsAdapter(mock_provider)
            return AnalyticsService(adapter=adapter)
        
        # Parse project ID to get provider UUID
        if ":" not in project_id:
            # Invalid format - return empty data, not mock
            logger.warning(f"Invalid project ID format: {project_id}, returning empty data")
            return AnalyticsService()
        
        provider_uuid, _ = project_id.split(":", 1)
        
        # Get PM provider from database using UUID (id field is UUID type)
        provider_conn = db.query(PMProviderConnection).filter(
            PMProviderConnection.id == provider_uuid,
            PMProviderConnection.is_active.is_(True)
        ).first()
        
        if not provider_conn:
            logger.warning(f"Provider with UUID {provider_uuid} not found, returning empty data")
            return AnalyticsService()
        
        # Create PM handler for this provider
        pm_handler = PMHandler.from_db_session(db)
        provider_instance = pm_handler._create_provider_instance(provider_conn)
        
        # Create analytics adapter
        adapter = PMProviderAnalyticsAdapter(provider_instance)
        
        logger.info(f"[Analytics] Created analytics service with real data for project {project_id}")
        
        # Return analytics service with real data
        return AnalyticsService(adapter=adapter)
    
    except Exception as e:
        logger.error(f"Error creating analytics service for project {project_id}: {e}", exc_info=True)
        # Return empty data on error (no mock fallback)
        return AnalyticsService()


@app.get("/api/analytics/projects/{project_id}/burndown")
async def get_burndown_chart(
    project_id: str,
    sprint_id: Optional[str] = None,
    scope_type: str = "story_points"
):
    """Get burndown chart for a project/sprint"""
    try:
        from database.connection import get_db_session
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            analytics_service = get_analytics_service(project_id, db)
            chart = await analytics_service.get_burndown_chart(
                project_id=project_id,
                sprint_id=sprint_id,
                scope_type=scope_type  # type: ignore
            )
            return chart.model_dump()
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    except Exception as e:
        logger.error(f"Failed to get burndown chart: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/projects/{project_id}/velocity")
async def get_velocity_chart(
    project_id: str,
    sprint_count: int = 6
):
    """Get velocity chart for a project"""
    try:
        from database.connection import get_db_session
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            analytics_service = get_analytics_service(project_id, db)
            chart = await analytics_service.get_velocity_chart(
                project_id=project_id,
                sprint_count=sprint_count
            )
            return chart.model_dump()
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    except Exception as e:
        logger.error(f"Failed to get velocity chart: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/sprints/{sprint_id}/report")
async def get_sprint_report(
    sprint_id: str,
    project_id: str
):
    """Get comprehensive sprint report"""
    try:
        from database.connection import get_db_session
        db_gen = get_db_session()
        db = next(db_gen)
        try:
            analytics_service = get_analytics_service(project_id, db)
            report = await analytics_service.get_sprint_report(sprint_id=sprint_id, project_id=project_id)
            return report.model_dump()
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    except NotImplementedError as e:
        logger.warning("Sprint report unavailable: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get sprint report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/projects/{project_id}/summary")
async def get_project_summary(project_id: str):
    """Get project analytics summary"""
    try:
        from database.connection import get_db_session
        db_gen = get_db_session()
        db = next(db_gen)
        try:
            analytics_service = get_analytics_service(project_id, db)
            summary = await analytics_service.get_project_summary(project_id=project_id)
            return summary
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    except NotImplementedError as e:
        logger.warning("Project summary unavailable: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get project summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/projects/{project_id}/cfd")
async def get_cfd_chart(
    project_id: str,
    sprint_id: Optional[str] = None,
    days_back: int = 30
):
    """Get Cumulative Flow Diagram for a project/sprint"""
    try:
        from database.connection import get_db_session
        db_gen = get_db_session()
        db = next(db_gen)
        try:
            analytics_service = get_analytics_service(project_id, db)
            chart = await analytics_service.get_cfd_chart(project_id=project_id, sprint_id=sprint_id, days_back=days_back)
            return chart.model_dump()
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    except NotImplementedError as e:
        logger.warning("CFD chart unavailable: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get CFD chart: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/projects/{project_id}/cycle-time")
async def get_cycle_time_chart(
    project_id: str,
    sprint_id: Optional[str] = None,
    days_back: int = 60
):
    """Get Cycle Time / Control Chart for a project/sprint"""
    try:
        from database.connection import get_db_session
        db_gen = get_db_session()
        db = next(db_gen)
        try:
            analytics_service = get_analytics_service(project_id, db)
            chart = await analytics_service.get_cycle_time_chart(project_id=project_id, sprint_id=sprint_id, days_back=days_back)
            return chart.model_dump()
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    except NotImplementedError as e:
        logger.warning("Cycle time chart unavailable: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get cycle time chart: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/projects/{project_id}/work-distribution")
async def get_work_distribution_chart(
    project_id: str,
    dimension: str = "assignee",
    sprint_id: Optional[str] = None
):
    """Get Work Distribution chart for a project"""
    try:
        from database.connection import get_db_session
        db_gen = get_db_session()
        db = next(db_gen)
        try:
            analytics_service = get_analytics_service(project_id, db)
            chart = await analytics_service.get_work_distribution_chart(project_id=project_id, dimension=dimension, sprint_id=sprint_id)
            return chart.model_dump()
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    except NotImplementedError as e:
        logger.warning("Work distribution chart unavailable: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get work distribution chart: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/projects/{project_id}/issue-trend")
async def get_issue_trend_chart(
    project_id: str,
    days_back: int = 30,
    sprint_id: Optional[str] = None
):
    """Get Issue Trend Analysis chart for a project"""
    try:
        from database.connection import get_db_session
        db_gen = get_db_session()
        db = next(db_gen)
        try:
            analytics_service = get_analytics_service(project_id, db)
            chart = await analytics_service.get_issue_trend_chart(project_id=project_id, days_back=days_back, sprint_id=sprint_id)
            return chart.model_dump()
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    except NotImplementedError as e:
        logger.warning("Issue trend chart unavailable: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get issue trend chart: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
