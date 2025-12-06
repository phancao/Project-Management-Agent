# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import asyncio
import base64
import json
import logging
import os
import requests
from datetime import datetime
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
from src.llms.model_providers import get_available_providers, detect_provider_from_config
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

# Import streaming utilities (extracted for better separation of concerns)
from src.server.streaming import (
    make_event as _make_event_new,
    safe_serialize as _safe_serialize_new,
    get_agent_name as _get_agent_name_new,
    process_tool_call_chunks as _process_tool_call_chunks_new,
    create_event_stream_message as _create_event_stream_message_new,
    process_message_chunk as _process_message_chunk_new,
    cache_thoughts,
    get_cached_thoughts,
    clear_thoughts_cache,
)

# Cache to store react_thoughts by message ID for AIMessageChunk processing
# This is needed because AIMessageChunk is streamed before the final AIMessage is created
# NOTE: Now uses streaming module cache, kept for backward compatibility
_react_thoughts_cache: dict[str, list] = {}
from src.server.config_request import ConfigResponse
from src.server.ai_provider_request import (
    AIProviderAPIKeyRequest,
    AIProviderAPIKeyResponse,
)
from src.server.search_provider_request import (
    SearchProviderAPIKeyRequest,
    SearchProviderAPIKeyResponse,
)
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
from pydantic import BaseModel
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
# ====================
# Request Models
# ====================


class PMTaskCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    sprint_id: Optional[str] = None
    assignee_id: Optional[str] = None
    epic_id: Optional[str] = None
    estimated_hours: Optional[float] = None


class TaskAssignmentRequest(BaseModel):
    assignee_id: Optional[str] = None

if os.name == "nt":
    # WindowsSelectorEventLoopPolicy is available on Windows
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()  # type: ignore
    )

INTERNAL_SERVER_ERROR_DETAIL = "Internal Server Error"

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(_app: FastAPI):  # FastAPI requires this parameter
    """
    Lifespan context manager for FastAPI app.
    
    Handles startup and shutdown events.
    """
    # Startup: Sync providers to MCP Server
    logger.info("[Startup] Starting provider sync to MCP Server...")
    try:
        from src.server.mcp_sync import check_and_sync_providers
        
        # Run sync in background to not block startup
        async def startup_sync():
            await asyncio.sleep(5)  # Wait for MCP Server to be ready
            try:
                result = await check_and_sync_providers()
                logger.info(f"[Startup] Provider sync completed: {result}")
            except Exception as e:
                logger.warning(f"[Startup] Provider sync failed (non-fatal): {e}")
        
        asyncio.create_task(startup_sync())
    except Exception as e:
        logger.warning(f"[Startup] Failed to start provider sync: {e}")
    
    yield
    
    # Shutdown: cleanup if needed
    logger.info("[Shutdown] Backend API shutting down...")


app = FastAPI(
    title="DeerFlow API",
    description="API for Deer",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker healthcheck."""
    return {"status": "healthy", "service": "backend-api"}


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


def get_default_mcp_settings() -> dict:
    """Get default MCP settings for PM tools and other MCP servers.
    
    This provides a default configuration when the frontend doesn't send
    mcp_settings in the request. Matches the configuration in workflow.py.
    
    Returns:
        dict: MCP server configuration with PM server and GitHub trending
    """
    return {
        "servers": {
            "pm-server": {
                "transport": "sse",
                "url": "http://pm_mcp_server:8080/sse",
                "headers": {
                    "X-MCP-API-Key": os.getenv(
                        "PM_MCP_API_KEY",
                        "mcp_a9b43d595b627e1e094209dea14bcb32f98867649ae181d4836dde87e283ccc3"
                    )
                },
                "enabled_tools": None,  # Enable all PM tools
                "add_to_agents": ["pm_agent"],  # Only PM Agent should have PM tools
            },
            "mcp-github-trending": {
                "transport": "stdio",
                "command": "uvx",
                "args": ["mcp-github-trending"],
                "enabled_tools": ["get_github_trending_repositories"],
                "add_to_agents": ["researcher"],
            }
        }
    }


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat responses for research tasks"""
    # Check if AI providers are configured
    from src.llms.llm import has_configured_ai_providers
    if not has_configured_ai_providers():
        error_message = (
            "No AI providers configured. Please configure an AI provider (OpenAI, Anthropic, etc.) "
            "in the Provider Management dialog before using the chat feature."
        )
        logger.warning("[chat_stream] No AI providers configured")
        raise HTTPException(status_code=400, detail=error_message)
    # Check if MCP server configuration is enabled
    mcp_enabled = get_bool_env("ENABLE_MCP_SERVER_CONFIGURATION", False)
    
    # Debug logging for MCP settings
    logger.info(f"[chat_stream] mcp_enabled={mcp_enabled}, request.mcp_settings={request.mcp_settings}")

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

    # Determine MCP settings to use
    # If mcp_enabled and no valid mcp_settings from request, use defaults
    if mcp_enabled:
        if request.mcp_settings and isinstance(request.mcp_settings, dict) and request.mcp_settings.get("servers"):
            mcp_settings_to_use = request.mcp_settings
            logger.info(f"[chat_stream] Using request mcp_settings with servers: {list(request.mcp_settings['servers'].keys())}")
        else:
            mcp_settings_to_use = get_default_mcp_settings()
            logger.info(f"[chat_stream] Using default mcp_settings with servers: {list(mcp_settings_to_use['servers'].keys())}")
    else:
        mcp_settings_to_use = {}
        logger.info("[chat_stream] MCP disabled, using empty mcp_settings")

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
            mcp_settings_to_use,
            request.enable_background_investigation or True,
            request.report_style or ReportStyle.ACADEMIC,
            request.enable_deep_thinking or False,
            request.enable_clarification or False,
            request.max_clarification_rounds or 3,
            request.locale or "en-US",
            request.interrupt_before_tools or [],
            request.model_provider,
            request.model_name,
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


def _get_agent_name(agent, message_metadata, message_chunk=None):
    """Extract agent name from agent tuple, message metadata, or message name attribute."""
    agent_name = "unknown"
    
    # Priority 1: Check message.name attribute (most reliable for AIMessage with name="pm_agent")
    if message_chunk and hasattr(message_chunk, 'name') and message_chunk.name:
        agent_name = message_chunk.name
    # Priority 2: Check agent tuple from LangGraph
    elif agent and len(agent) > 0:
        agent_name = agent[0].split(":")[0] if ":" in agent[0] else agent[0]
    # Priority 3: Check message metadata
    else:
        agent_name = message_metadata.get("langgraph_node", "unknown")
    
    return agent_name


def _safe_serialize(obj):
    """Safely serialize an object to JSON-compatible format."""
    if isinstance(obj, str):
        return obj
    try:
        # Try direct serialization first
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        # If it fails, convert to string representation
        if isinstance(obj, dict):
            return {k: _safe_serialize(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [_safe_serialize(item) for item in obj]
        else:
            return str(obj)


def _create_event_stream_message(
    message_chunk, message_metadata, thread_id, agent_name
):
    """Create base event stream message.
    
    Ensures every message has a valid ID by generating one if missing.
    This prevents frontend research block failures caused by undefined IDs.
    """
    content = message_chunk.content
    if not isinstance(content, str):
        # Safely serialize content, handling non-JSON-serializable objects
        content = json.dumps(_safe_serialize(content), ensure_ascii=False)

    # CRITICAL: Ensure message ID is always present
    # Some messages arrive without ID, causing frontend research block failures
    message_id = getattr(message_chunk, 'id', None)
    if not message_id:
        message_id = f"run--{uuid4().hex}"
        logger.warning(
            f"[_create_event_stream_message] Generated ID {message_id} for {agent_name} message (was None)"
        )
        # Set ID on message_chunk for consistency downstream
        if hasattr(message_chunk, 'id'):
            try:
                message_chunk.id = message_id
            except AttributeError:
                pass  # Some message types have read-only id

    event_stream_message = {
        "thread_id": thread_id,
        "agent": agent_name,
        "id": message_id,
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
    
    # Add react_thoughts if available (check response_metadata first, then additional_kwargs)
    react_thoughts = None
    if hasattr(message_chunk, 'response_metadata') and message_chunk.response_metadata:
        react_thoughts = message_chunk.response_metadata.get("react_thoughts")
    if not react_thoughts and hasattr(message_chunk, 'additional_kwargs') and message_chunk.additional_kwargs:
        react_thoughts = message_chunk.additional_kwargs.get("react_thoughts")
    
    if react_thoughts:
        event_stream_message["react_thoughts"] = react_thoughts

    # Include finish_reason from response_metadata or message_metadata
    finish_reason = None
    if hasattr(message_chunk, 'response_metadata') and message_chunk.response_metadata:
        finish_reason = message_chunk.response_metadata.get("finish_reason")
    if not finish_reason:
        finish_reason = message_metadata.get("finish_reason")
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

    agent_name = _get_agent_name(agent, message_metadata, message_chunk)
    safe_agent_name = sanitize_agent_name(agent_name)
    safe_thread_id = sanitize_thread_id(thread_id)
    logger.debug(
        f"[{safe_thread_id}] _process_message_chunk started for "
        f"agent={safe_agent_name}"
    )
    logger.debug(f"[{safe_thread_id}] Extracted agent_name: {safe_agent_name} (from message.name={getattr(message_chunk, 'name', 'N/A')}, agent={agent}, metadata={message_metadata.get('langgraph_node', 'N/A')})")
    
    event_stream_message = _create_event_stream_message(
        message_chunk, message_metadata, thread_id, agent_name
    )
    
    # Check cache for react_thoughts if not already in message
    if agent_name in ["pm_agent", "react_agent"]:
        message_id = event_stream_message.get("id")
        if message_id and message_id in _react_thoughts_cache and "react_thoughts" not in event_stream_message:
            cached_thoughts = _react_thoughts_cache[message_id]
            event_stream_message["react_thoughts"] = cached_thoughts
            if isinstance(message_chunk, AIMessageChunk):
                if not message_chunk.additional_kwargs:
                    message_chunk.additional_kwargs = {}
                message_chunk.additional_kwargs["react_thoughts"] = cached_thoughts

    if isinstance(message_chunk, ToolMessage):
        # Tool Message - Return the result of the tool call
        event_stream_message["tool_call_id"] = message_chunk.tool_call_id
        yield _make_event("tool_call_result", event_stream_message)
        
    elif isinstance(message_chunk, AIMessageChunk):
        # AI Message Chunk - Streaming response
        if message_chunk.tool_calls:
            # Complete tool calls
            event_stream_message["tool_calls"] = message_chunk.tool_calls
            
            # Include react_thoughts if available
            if "react_thoughts" not in event_stream_message:
                chunk_thoughts = None
                if hasattr(message_chunk, 'response_metadata') and message_chunk.response_metadata:
                    chunk_thoughts = message_chunk.response_metadata.get("react_thoughts")
                if not chunk_thoughts and hasattr(message_chunk, 'additional_kwargs') and message_chunk.additional_kwargs:
                    chunk_thoughts = message_chunk.additional_kwargs.get("react_thoughts")
                if chunk_thoughts:
                    event_stream_message["react_thoughts"] = chunk_thoughts
            
            # Process tool_call_chunks
            processed_chunks = _process_tool_call_chunks(message_chunk.tool_call_chunks)
            if processed_chunks:
                event_stream_message["tool_call_chunks"] = processed_chunks
            
            yield _make_event("tool_calls", event_stream_message)
        elif message_chunk.tool_call_chunks:
            # Streaming tool call chunks
            processed_chunks = _process_tool_call_chunks(message_chunk.tool_call_chunks)
            if processed_chunks:
                event_stream_message["tool_call_chunks"] = processed_chunks
            yield _make_event("tool_call_chunks", event_stream_message)
        else:
            # Regular content chunk
            yield _make_event("message_chunk", event_stream_message)
    elif isinstance(message_chunk, AIMessage):
        # Full AIMessage (not chunk) - used for state update streaming
        # Ensure react_thoughts are included
        if "react_thoughts" not in event_stream_message:
            react_thoughts = None
            if hasattr(message_chunk, 'response_metadata') and message_chunk.response_metadata:
                react_thoughts = message_chunk.response_metadata.get("react_thoughts")
            if not react_thoughts and hasattr(message_chunk, 'additional_kwargs') and message_chunk.additional_kwargs:
                react_thoughts = message_chunk.additional_kwargs.get("react_thoughts")
            if react_thoughts:
                event_stream_message["react_thoughts"] = react_thoughts
        
        # Include tool_calls if present
        if hasattr(message_chunk, 'tool_calls') and message_chunk.tool_calls:
            event_stream_message["tool_calls"] = message_chunk.tool_calls
            yield _make_event("tool_calls", event_stream_message)
        else:
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
        logger.info(f"[{safe_thread_id}] 🎬 Starting graph.astream with workflow_input keys: {list(workflow_input.keys()) if isinstance(workflow_input, dict) else 'Command object'}")
        logger.info(f"[{safe_thread_id}] 🎬 Graph entry point should be: START → coordinator")
        async for agent, stream_type, event_data in graph_instance.astream(
            workflow_input,
            config=workflow_config,
            stream_mode=["messages", "updates", "debug"],  # Added debug mode
            subgraphs=True,
            debug=False,  # Set to True for verbose debug output
        ):
            # Log first few events to track entry point
            if event_count < 5:
                logger.info(f"[{safe_thread_id}] 🎯 Graph event #{event_count}: agent={agent}, stream_type={stream_type}")
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
                            
                            # Check if this is a quota error - we'll handle it in the main exception handler
                            # since debug events don't stream to client
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
                    # Log message type and agent for debugging
                    msg_type = type(message_chunk).__name__
                    chunk_content = ""
                    if hasattr(message_chunk, 'content'):
                        chunk_content = str(message_chunk.content)[:50] if message_chunk.content else ""
                    chunk_name = getattr(message_chunk, 'name', 'N/A')
                    logger.info(
                        f"[{safe_thread_id}] 📨 messages stream: type={msg_type}, "
                        f"agent_path={agent}, chunk_name={chunk_name}, "
                        f"content_preview=\"{chunk_content}...\""
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
                        
                        # DEBUG: Log all node updates for pm_agent/react_agent
                        if node_name in ["pm_agent", "react_agent"]:
                            logger.info(
                                f"[{safe_thread_id}] 🔍 [DEBUG] Processing node_update for {node_name}: "
                                f"keys={list(node_update.keys())}, "
                                f"has_react_thoughts={'react_thoughts' in node_update}, "
                                f"has_messages={'messages' in node_update}"
                            )
                        
                        # Stream plan updates
                        if "current_plan" in node_update:
                            current_plan = node_update.get("current_plan")
                            if current_plan:
                                # Extract plan information
                                plan_data = {}
                                
                                # Handle different types of current_plan (string, dict, or Plan object)
                                plan_obj = None
                                if isinstance(current_plan, str):
                                    # Try to parse JSON string
                                    try:
                                        import json
                                        plan_dict = json.loads(current_plan)
                                        plan_obj = plan_dict
                                    except (json.JSONDecodeError, TypeError):
                                        logger.warning(f"[{safe_thread_id}] Could not parse current_plan as JSON string")
                                        plan_obj = None
                                elif isinstance(current_plan, dict):
                                    plan_obj = current_plan
                                else:
                                    # Assume it's a Plan object with attributes
                                    plan_obj = current_plan
                                
                                # Extract title
                                if isinstance(plan_obj, dict):
                                    plan_data["title"] = plan_obj.get("title", "")
                                    # Extract steps
                                    steps = plan_obj.get("steps", [])
                                    plan_data["steps"] = [
                                        {
                                            "title": step.get("title", "") if isinstance(step, dict) else getattr(step, "title", ""),
                                            "description": step.get("description", "") if isinstance(step, dict) else getattr(step, "description", ""),
                                            "step_type": (
                                                step.get("step_type", {}).get("value") if isinstance(step.get("step_type"), dict)
                                                else step.get("step_type") if isinstance(step, dict)
                                                else getattr(step.step_type, "value", None) if hasattr(getattr(step, "step_type", None), "value")
                                                else str(getattr(step, "step_type", "")) if hasattr(step, "step_type")
                                                else None
                                            ),
                                            "execution_res": (
                                                step.get("execution_res") if isinstance(step, dict)
                                                else getattr(step, "execution_res", None)
                                            ),
                                        }
                                        for step in steps
                                    ] if steps else []
                                elif hasattr(plan_obj, 'title'):
                                    # Plan object with attributes
                                    plan_data["title"] = plan_obj.title if not callable(plan_obj.title) else ""
                                    if hasattr(plan_obj, 'steps'):
                                        steps = plan_obj.steps if not callable(plan_obj.steps) else []
                                        plan_data["steps"] = [
                                            {
                                                "title": step.title if hasattr(step, 'title') and not callable(step.title) else "",
                                                "description": step.description if hasattr(step, 'description') and not callable(step.description) else "",
                                                "step_type": (
                                                    step.step_type.value
                                                    if hasattr(step, 'step_type') and hasattr(step.step_type, 'value')
                                                    else str(step.step_type) if hasattr(step, 'step_type')
                                                    else None
                                                ),
                                                "execution_res": (
                                                    step.execution_res
                                                    if hasattr(step, 'execution_res')
                                                    else None
                                                ),
                                            }
                                            for step in steps
                                        ] if steps else []
                                
                                # Debug current_plan structure
                                try:
                                    logger.info(f"[{safe_thread_id}] Inspecting current_plan: type={type(current_plan)}")
                                    if hasattr(current_plan, 'title'):
                                        logger.info(f"[{safe_thread_id}] current_plan.title type: {type(current_plan.title)}")
                                    if hasattr(current_plan, 'steps'):
                                        logger.info(f"[{safe_thread_id}] current_plan.steps type: {type(current_plan.steps)}")
                                        if current_plan.steps:
                                            first_step = current_plan.steps[0]
                                            logger.info(f"[{safe_thread_id}] First step type: {type(first_step)}")
                                            if hasattr(first_step, 'step_type'):
                                                logger.info(f"[{safe_thread_id}] First step step_type type: {type(first_step.step_type)}")
                                except Exception as e:
                                    logger.error(f"[{safe_thread_id}] Error inspecting current_plan: {e}")

                                try:
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
                                except Exception as e:
                                    logger.error(f"[{safe_thread_id}] Error streaming plan_update: {e}")
                                    # Try to identify non-serializable item
                                    try:
                                        json.dumps(plan_data)
                                    except TypeError as json_err:
                                        logger.error(f"[{safe_thread_id}] JSON serialization error in plan_data: {json_err}")
                                
                                # Also emit step_progress for current step
                                # Emit progress for each step in the plan
                                logger.info(f"[{safe_thread_id}] Checking for step_progress emission. current_plan type: {type(current_plan)}")
                                if hasattr(current_plan, 'steps'):
                                    logger.info(f"[{safe_thread_id}] current_plan has steps. Count: {len(current_plan.steps) if current_plan.steps else 0}")
                                else:
                                    logger.info(f"[{safe_thread_id}] current_plan does NOT have steps attribute")

                                if hasattr(current_plan, 'steps') and current_plan.steps:
                                    # Count completed steps to determine current step
                                    completed_count = sum(
                                        1 for step in current_plan.steps 
                                        if hasattr(step, 'execution_res') and step.execution_res
                                    )
                                    # Current step is the first incomplete one, or the last one if all complete
                                    current_step_idx = min(completed_count, len(current_plan.steps) - 1)
                                    current_step = current_plan.steps[current_step_idx]
                                    
                                    logger.info(
                                        f"[{safe_thread_id}] Streaming step progress: "
                                        f"Step {current_step_idx + 1}/{len(current_plan.steps)}: {current_step.title}"
                                    )
                                    yield _make_event(
                                        "step_progress",
                                        {
                                            "thread_id": thread_id,
                                            "agent": node_name,
                                            "role": "assistant",
                                            "step_title": current_step.title,
                                            "step_description": current_step.description if hasattr(current_step, 'description') else "",
                                            "step_index": current_step_idx,
                                            "total_steps": len(current_plan.steps),
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
                        
                        # Cursor-style: Stream react_thoughts for ReAct agent and PM Agent
                        # We need to stream thoughts even if message content is empty (tool calls only)
                        # Note: node_name might be "agent" but we need to check messages to get actual agent name
                        node_react_thoughts = None
                        actual_agent_name = None
                        
                        # Debug: Log node_update keys for pm_agent/react_agent nodes
                        if node_name in ["react_agent", "pm_agent", "agent"]:
                            logger.debug(
                                f"[{safe_thread_id}] 🔍 Checking node_update for {node_name}: "
                                f"keys={list(node_update.keys())}, has_react_thoughts={'react_thoughts' in node_update}"
                            )
                        
                        # Check if react_thoughts exist in node_update
                        if "react_thoughts" in node_update:
                            # Determine actual agent name from messages if node_name is generic "agent"
                            if node_name == "agent" and "messages" in node_update:
                                messages = node_update.get("messages", [])
                                for msg in messages:
                                    if isinstance(msg, AIMessage) and hasattr(msg, 'name') and msg.name:
                                        actual_agent_name = msg.name
                                        if actual_agent_name in ["react_agent", "pm_agent"]:
                                            break
                            elif node_name in ["react_agent", "pm_agent"]:
                                actual_agent_name = node_name
                            
                            if actual_agent_name in ["react_agent", "pm_agent"]:
                                node_react_thoughts = node_update.get("react_thoughts", [])
                                if node_react_thoughts:
                                    logger.info(
                                        f"[{safe_thread_id}] 💭 Found react_thoughts in node_update for {actual_agent_name} (node: {node_name}): "
                                        f"{len(node_react_thoughts)} thoughts: {[t.get('thought', '')[:50] if isinstance(t, dict) else str(t)[:50] for t in node_react_thoughts[:3]]}"
                                    )
                                    # CRITICAL FIX: Store thoughts in cache for AIMessageChunk processing
                                    # Find the message ID from messages in node_update
                                    if "messages" in node_update:
                                        for msg in node_update.get("messages", []):
                                            if isinstance(msg, AIMessage) and hasattr(msg, 'id') and msg.id:
                                                _react_thoughts_cache[msg.id] = node_react_thoughts
                                                logger.info(
                                                    f"[{safe_thread_id}] ✅ Cached {len(node_react_thoughts)} react_thoughts for message {msg.id} "
                                                    f"for AIMessageChunk processing"
                                                )
                                                break
                                    logger.debug(
                                        f"[{safe_thread_id}] 💭 Thoughts will be attached to agent message when it's streamed"
                                    )
                                else:
                                    logger.warning(
                                        f"[{safe_thread_id}] ⚠️ react_thoughts key exists but is empty for {actual_agent_name} (node: {node_name})"
                                    )
                            else:
                                logger.debug(
                                    f"[{safe_thread_id}] 🔍 react_thoughts found but actual_agent_name={actual_agent_name} not in [react_agent, pm_agent]"
                                )
                        
                        # Stream step progress updates when current_step_index changes
                        if "current_step_index" in node_update or "total_steps" in node_update:
                            current_step_index = node_update.get("current_step_index")
                            total_steps = node_update.get("total_steps")
                            
                            # Get current plan to extract step details
                            current_plan = node_update.get("current_plan")
                            if not current_plan:
                                # Try to get from previous state if not in update
                                try:
                                    current_plan = event_data.get("current_plan")
                                except:
                                    pass
                            
                            if current_step_index is not None and total_steps is not None and current_plan:
                                # Get the current step details
                                step_title = f"Step {current_step_index + 1}"
                                step_description = ""
                                
                                if hasattr(current_plan, 'steps') and current_plan.steps:
                                    if current_step_index < len(current_plan.steps):
                                        current_step = current_plan.steps[current_step_index]
                                        step_title = current_step.title
                                        step_description = current_step.description if hasattr(current_step, 'description') else ""
                                
                                logger.info(
                                    f"[{safe_thread_id}] Streaming step progress: "
                                    f"Step {current_step_index + 1}/{total_steps}: {step_title}"
                                )
                                
                                yield _make_event(
                                    "step_progress",
                                    {
                                        "thread_id": thread_id,
                                        "agent": node_name,
                                        "role": "assistant",
                                        "step_title": step_title,
                                        "step_description": step_description,
                                        "step_index": current_step_index,
                                        "total_steps": total_steps,
                                    }
                                )
                        
                        # Stream messages from state updates
                        # (e.g., reporter's final report)
                        # NOTE: For reporter messages, we DON'T stream from
                        # state updates because they should already be streamed
                        # in the "messages" stream. Streaming here would create
                        # a duplicate message with a different ID, causing the
                        # frontend to not recognize the finish_reason properly.
                        # REAL PROGRESSIVE STREAMING: Stream planner's thought and step thoughts
                        # This ensures the flow is: Planner Thought → Step Thought → Action (tool call) → Observation
                        
                        # 1. Stream PLANNER'S overall thought (reasoning for the entire plan)
                        if "current_plan" in node_update and node_name == "planner":
                            current_plan = node_update.get("current_plan")
                            if current_plan:
                                # Extract planner's thought from the plan
                                planner_thought = None
                                if isinstance(current_plan, dict):
                                    planner_thought = current_plan.get("thought", "")
                                elif hasattr(current_plan, 'thought'):
                                    planner_thought = getattr(current_plan, 'thought', '')
                                
                                if planner_thought and planner_thought.strip():
                                    logger.info(
                                        f"[{safe_thread_id}] 💭 [PLANNER] Found planner thought: {planner_thought[:50]}..."
                                    )
                                    
                                    # Find message ID from planner message
                                    message_id = None
                                    if "messages" in node_update:
                                        messages = node_update.get("messages", [])
                                        for msg in messages:
                                            if isinstance(msg, AIMessage) and hasattr(msg, 'id') and msg.id:
                                                message_id = msg.id
                                                break
                                    
                                    if not message_id:
                                        message_id = f"run--{uuid4().hex}"
                                    
                                    planner_thought_event = {
                                        "thought": planner_thought.strip(),
                                        "before_tool": True,
                                        "step_index": -1  # -1 indicates planner's overall thought (before any steps)
                                    }
                                    
                                    thoughts_event = {
                                        "thread_id": thread_id,
                                        "agent": "planner",
                                        "id": message_id,
                                        "role": "assistant",
                                        "react_thoughts": [planner_thought_event]
                                    }
                                    logger.info(
                                        f"[{safe_thread_id}] 💭 [PLANNER] Streaming planner's overall thought (messageId={message_id})"
                                    )
                                    yield _make_event("thoughts", thoughts_event)
                                    
                                    # Small delay
                                    import asyncio
                                    await asyncio.sleep(0.01)
                        
                        # 2. Stream thought for current step BEFORE agent execution
                        # This triggers when PLANNER sets current_step_index, BEFORE pm_agent/react_agent executes
                        current_step_thought = None
                        if "current_plan" in node_update and "current_step_index" in node_update:
                            current_plan = node_update.get("current_plan")
                            current_step_index = node_update.get("current_step_index")
                            
                            # Only stream thought if this is from planner setting up a step for execution
                            # Planner sends current_step_index when routing to research_team
                            if current_plan and current_step_index is not None and node_name == "planner":
                                logger.info(
                                    f"[{safe_thread_id}] 💭 [PROGRESSIVE] Planner set current_step_index={current_step_index}, "
                                    f"extracting thought for step BEFORE execution"
                                )
                                
                                # Extract plan structure (handle different types: dict, object, string)
                                plan_steps = None
                                if isinstance(current_plan, dict):
                                    plan_steps = current_plan.get("steps", [])
                                elif hasattr(current_plan, 'steps'):
                                    plan_steps = current_plan.steps
                                
                                if plan_steps and 0 <= current_step_index < len(plan_steps):
                                    current_step = plan_steps[current_step_index]
                                    step_description = None
                                    step_type = None
                                    
                                    if isinstance(current_step, dict):
                                        step_description = current_step.get("description", "")
                                        step_type = current_step.get("step_type", "")
                                    elif hasattr(current_step, 'description'):
                                        step_description = getattr(current_step, 'description', '')
                                        step_type = getattr(current_step, 'step_type', '')
                                        if hasattr(step_type, 'value'):
                                            step_type = step_type.value
                                    
                                    if step_description and step_description.strip():
                                        # Determine agent based on step_type
                                        # pm_agent handles: pm (project management), pm_api
                                        # react_agent handles: research, code, etc.
                                        agent_for_step = "pm_agent" if step_type in ["pm", "pm_api"] else "react_agent"
                                        
                                        current_step_thought = {
                                            "thought": step_description.strip(),
                                            "before_tool": True,
                                            "step_index": current_step_index
                                        }
                                        logger.info(
                                            f"[{safe_thread_id}] 💭 [PROGRESSIVE] Extracted thought for step {current_step_index} "
                                            f"(type={step_type}, agent={agent_for_step}): {step_description[:50]}..."
                                        )
                                        
                                        # Generate message ID for this thought
                                        message_id = f"run--{uuid4().hex}"
                                        
                                        thoughts_event = {
                                            "thread_id": thread_id,
                                            "agent": agent_for_step,
                                            "id": message_id,
                                            "role": "assistant",
                                            "react_thoughts": [current_step_thought]
                                        }
                                        logger.info(
                                            f"[{safe_thread_id}] 💭 [PROGRESSIVE] Streaming thought for step {current_step_index} "
                                            f"BEFORE execution by {agent_for_step} (messageId={message_id})"
                                        )
                                        yield _make_event("thoughts", thoughts_event)
                                        
                                        # Small delay to ensure thought is processed before tool calls
                                        import asyncio
                                        await asyncio.sleep(0.01)  # 10ms delay
                                else:
                                    logger.warning(
                                        f"[{safe_thread_id}] ⚠️ [PROGRESSIVE] current_step_index={current_step_index} "
                                        f"out of range for plan with {len(plan_steps) if plan_steps else 0} steps"
                                    )
                        
                        # ROOT CAUSE FIX: Stream thoughts as separate events FIRST, before processing messages
                        # Thoughts should have their own channel, not be attached to messages
                        # Stream thoughts if they exist in node_update, regardless of whether messages exist
                        # CRITICAL: node_name is the internal LangGraph node name (e.g., "agent", "tools", "pre_model_hook")
                        # We need to extract the actual agent name from messages in node_update
                        actual_agent_name = None
                        if "react_thoughts" in node_update:
                            # Try to determine agent name from messages
                            if "messages" in node_update:
                                messages = node_update.get("messages", [])
                                for msg in messages:
                                    if isinstance(msg, AIMessage) and hasattr(msg, 'name') and msg.name:
                                        if msg.name in ["pm_agent", "react_agent"]:
                                            actual_agent_name = msg.name
                                            break
                            
                            # If node_name itself is the agent name, use it
                            if not actual_agent_name and node_name in ["pm_agent", "react_agent"]:
                                actual_agent_name = node_name
                            
                            logger.info(
                                f"[{safe_thread_id}] 🔍 [DEBUG] Checking for thoughts streaming: node_name={node_name}, "
                                f"actual_agent_name={actual_agent_name}, "
                                f"has_react_thoughts={'react_thoughts' in node_update}, "
                                f"node_update_keys={list(node_update.keys())}"
                            )
                            
                            if actual_agent_name in ["pm_agent", "react_agent"]:
                                node_thoughts = node_update.get("react_thoughts", [])
                                logger.info(
                                    f"[{safe_thread_id}] 🔍 [DEBUG] Found react_thoughts in node_update: count={len(node_thoughts) if node_thoughts else 0}"
                                )
                                if node_thoughts:
                                    # Check if we've already streamed the current step's thought progressively
                                    # If so, filter it out to avoid duplicates (frontend will deduplicate, but this is cleaner)
                                    already_streamed_step_index = None
                                    if current_step_thought:
                                        already_streamed_step_index = current_step_thought.get("step_index")
                                    
                                    # Filter out thoughts that were already streamed progressively
                                    thoughts_to_stream = []
                                    for thought in node_thoughts:
                                        thought_step_index = thought.get("step_index")
                                        # Only stream if not already streamed, or if it's a different thought
                                        if already_streamed_step_index is None or thought_step_index != already_streamed_step_index:
                                            thoughts_to_stream.append(thought)
                                        else:
                                            logger.debug(
                                                f"[{safe_thread_id}] ⏭️ Skipping thought for step {thought_step_index} "
                                                f"(already streamed progressively)"
                                            )
                                    
                                    # Stream remaining thoughts (if any) - these are thoughts from previous steps or all steps
                                    if thoughts_to_stream:
                                        # Find message ID from messages if available, or generate one
                                        message_id = None
                                        if "messages" in node_update:
                                            messages = node_update.get("messages", [])
                                            # Try to find a message ID from messages
                                            for msg in messages:
                                                if isinstance(msg, AIMessage) and hasattr(msg, 'id') and msg.id:
                                                    message_id = msg.id
                                                    break
                                        
                                        if not message_id:
                                            message_id = f"run--{uuid4().hex}"
                                        
                                        logger.info(
                                            f"[{safe_thread_id}] 💭 Streaming {len(thoughts_to_stream)} additional thoughts "
                                            f"for {actual_agent_name} (node: {node_name}, messageId={message_id})"
                                        )
                                        
                                        thoughts_event = {
                                            "thread_id": thread_id,
                                            "agent": actual_agent_name,
                                            "id": message_id,
                                            "role": "assistant",
                                            "react_thoughts": thoughts_to_stream
                                        }
                                        yield _make_event("thoughts", thoughts_event)
                                        
                                        # Small delay to ensure thoughts are processed before tool_calls
                                        import asyncio
                                        await asyncio.sleep(0.01)  # 10ms delay before tool_calls
                                    else:
                                        logger.debug(
                                            f"[{safe_thread_id}] ⏭️ All thoughts already streamed progressively, skipping batch stream"
                                        )
                        
                        # Only stream non-reporter messages from state updates.
                        if "messages" in node_update and node_name != "reporter":
                            messages = node_update.get("messages", [])
                            if messages:
                                # Get the latest message
                                import sys
                                sys.stderr.write(f"\n🔍 CHECKING MESSAGES: node_name='{node_name}', messages_count={len(messages)}\n")
                                for msg in messages:
                                    msg_type = type(msg).__name__
                                    msg_name = getattr(msg, 'name', 'N/A')
                                    is_ai = isinstance(msg, AIMessage)
                                    name_match = msg_name == node_name
                                    sys.stderr.write(f"🔍 Message: type={msg_type}, name={msg_name}, is_AIMessage={is_ai}, name_matches={name_match}\n")
                                sys.stderr.flush()
                                
                                # Find the LAST AIMessage with content (that's the final response)
                                # Earlier messages might be tool-calling messages with empty content
                                final_ai_message = None
                                for msg in reversed(messages):
                                    if isinstance(msg, AIMessage) and msg.name == node_name:
                                        msg_content = getattr(msg, 'content', '') or ''
                                        # Pick the last message with content, or any message if none have content
                                        if msg_content or final_ai_message is None:
                                            final_ai_message = msg
                                            if msg_content:  # Found message with content, use it
                                                break
                                
                                # CRITICAL: Find AIMessage with tool_calls FIRST and attach thoughts to it
                                # This ensures thoughts are available when tool_calls are streamed
                                tool_call_ai_message = None
                                for msg in messages:
                                    if isinstance(msg, AIMessage) and msg.name == node_name:
                                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                            tool_call_ai_message = msg
                                            logger.info(
                                                f"[{safe_thread_id}] 🔍 Found AIMessage with tool_calls: {len(msg.tool_calls)} calls"
                                            )
                                            break
                                
                                # Process ToolMessages
                                for msg in messages:
                                    if isinstance(msg, ToolMessage):
                                        logger.info(
                                            f"[{safe_thread_id}] 🔧 Processing ToolMessage from updates stream: "
                                            f"tool_call_id={msg.tool_call_id}"
                                        )
                                        msg_metadata = {
                                            "langgraph_node": node_name,
                                        }
                                        async for event in _process_message_chunk(
                                            msg,
                                            msg_metadata,
                                            thread_id,
                                            (node_name,),
                                        ):
                                            yield event
                                
                                # Process AIMessage with tool_calls (stream tool_calls event WITHOUT thoughts)
                                # NOTE: Thoughts are already streamed above before this block
                                if tool_call_ai_message:
                                    logger.info(
                                        f"[{safe_thread_id}] 🔧 Streaming AIMessage with tool_calls: "
                                        f"{len(tool_call_ai_message.tool_calls)} calls"
                                    )
                                    msg_metadata = {
                                        "langgraph_node": node_name,
                                        "finish_reason": "tool_calls"
                                    }
                                    async for event in _process_message_chunk(
                                        tool_call_ai_message,
                                        msg_metadata,
                                        thread_id,
                                        (node_name,),
                                    ):
                                        yield event
                                
                                # Process the final AIMessage (with content)
                                if final_ai_message:
                                    msg = final_ai_message
                                    import sys
                                    sys.stderr.write(f"\n✨ STREAMING MESSAGE: node_name='{node_name}', content_len={len(msg.content)}\n")
                                    sys.stderr.flush()
                                    
                                    logger.info(
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
                                    
                                    # Cursor-style: Add react_thoughts to metadata if available
                                    # Check multiple sources in order of reliability:
                                    # 1. response_metadata (most reliable, preserved through LangGraph)
                                    # 2. additional_kwargs (may be lost during serialization)
                                    # 3. node_update (may not be present)
                                    # Support both react_agent and pm_agent
                                    react_thoughts = None
                                    
                                    # Method 1: Check response_metadata first (most reliable)
                                    if hasattr(msg, 'response_metadata') and msg.response_metadata:
                                        metadata_thoughts = msg.response_metadata.get("react_thoughts")
                                        if metadata_thoughts:
                                            react_thoughts = metadata_thoughts
                                            logger.info(f"[{safe_thread_id}] ✅ Found react_thoughts in message.response_metadata for {node_name}: {len(react_thoughts) if react_thoughts else 0} thoughts")
                                    
                                    # Method 2: Check additional_kwargs
                                    if not react_thoughts and hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
                                        msg_thoughts = msg.additional_kwargs.get("react_thoughts")
                                        if msg_thoughts:
                                            react_thoughts = msg_thoughts
                                            logger.info(f"[{safe_thread_id}] ✅ Found react_thoughts in message.additional_kwargs for {node_name}: {len(react_thoughts) if react_thoughts else 0} thoughts")
                                    
                                    # Method 3: Check node_update (fallback)
                                    if not react_thoughts and "react_thoughts" in node_update and node_name in ["react_agent", "pm_agent"]:
                                        react_thoughts = node_update.get("react_thoughts", [])
                                        logger.info(f"[{safe_thread_id}] ✅ Found react_thoughts in node_update for {node_name}: {len(react_thoughts) if react_thoughts else 0} thoughts")
                                    
                                    # Debug: Log what we're checking
                                    logger.info(f"[{safe_thread_id}] 🔍 Checking for thoughts: node_update_keys={list(node_update.keys())}, msg_has_additional_kwargs={hasattr(msg, 'additional_kwargs')}, additional_kwargs={msg.additional_kwargs if hasattr(msg, 'additional_kwargs') else 'N/A'}")
                                    
                                    if react_thoughts:
                                        # Store thoughts in both additional_kwargs and response_metadata for maximum compatibility
                                        if not hasattr(msg, 'additional_kwargs') or not msg.additional_kwargs:
                                            msg.additional_kwargs = {}
                                        msg.additional_kwargs["react_thoughts"] = react_thoughts
                                        
                                        if not hasattr(msg, 'response_metadata') or not msg.response_metadata:
                                            msg.response_metadata = {}
                                        msg.response_metadata["react_thoughts"] = react_thoughts
                                        
                                        logger.info(
                                            f"[{safe_thread_id}] ✅ Added {len(react_thoughts)} react_thoughts to message {msg.id} "
                                            f"for streaming ({node_name}): {[t.get('thought', '')[:50] if isinstance(t, dict) else str(t)[:50] for t in react_thoughts[:3]]}"
                                        )
                                    else:
                                        logger.warning(
                                            f"[{safe_thread_id}] ⚠️ No react_thoughts found for {node_name} message {msg.id} "
                                            f"(node_update has react_thoughts: {'react_thoughts' in node_update})"
                                        )
                                    
                                    # CRITICAL: Ensure thoughts are in the message BEFORE calling _process_message_chunk
                                    # _process_message_chunk calls _create_event_stream_message which needs thoughts
                                    if react_thoughts:
                                        # Double-check thoughts are still in the message
                                        if not hasattr(msg, 'response_metadata') or not msg.response_metadata:
                                            msg.response_metadata = {}
                                        if not hasattr(msg, 'additional_kwargs') or not msg.additional_kwargs:
                                            msg.additional_kwargs = {}
                                        msg.response_metadata["react_thoughts"] = react_thoughts
                                        msg.additional_kwargs["react_thoughts"] = react_thoughts
                                        logger.info(f"[{safe_thread_id}] ✅ Verified thoughts are in message {msg.id} before streaming")
                                    
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
        
        # Check for quota/rate limit errors and provide user-friendly message
        error_str = str(e)
        error_type = type(e).__name__
        
        is_quota_error = (
            "429" in error_str or
            "insufficient_quota" in error_str.lower() or
            "quota" in error_str.lower() or
            "rate limit" in error_str.lower() or
            "RateLimitError" in error_type or
            "exceeded" in error_str.lower() and "quota" in error_str.lower()
        )
        
        if is_quota_error:
            # Extract provider name from error if available
            provider_name = "OpenAI"  # Default
            if "openai" in error_str.lower():
                provider_name = "OpenAI"
            elif "anthropic" in error_str.lower():
                provider_name = "Anthropic"
            elif "google" in error_str.lower():
                provider_name = "Google"
            
            quota_message = f"""⚠️ **AI Provider Quota Exceeded**

Your {provider_name} account has exceeded its usage quota or rate limit. 

**To continue using the service, please:**

1. **Check your {provider_name} account billing:**
   - Visit your {provider_name} dashboard
   - Review your usage and billing information
   - Add payment method or increase your quota

2. **For OpenAI:** https://platform.openai.com/account/billing
3. **For Anthropic:** https://console.anthropic.com/settings/billing
4. **For Google:** https://console.cloud.google.com/billing

Once you've added credits or increased your quota, you can try your request again.

**Error Details:** {error_str[:200]}"""
            
            # Stream as a message_chunk so frontend displays it properly
            quota_event = {
                "id": str(uuid4()),
                "thread_id": thread_id,
                "agent": "system",
                "role": "assistant",
                "content": quota_message,
                "finish_reason": "error",
                "error_type": "quota_exceeded",
                "provider": provider_name
            }
            # Use the same format as other message chunks
            json_data = json.dumps(quota_event, ensure_ascii=False, separators=(",", ":"))
            yield f"event: message_chunk\ndata: {json_data}\n\n"
        else:
            # For other errors, use the standard error event
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
    model_provider: Optional[str] = None,
    model_name: Optional[str] = None,
):
    # Set model selection in context for LLM initialization
    if model_provider or model_name:
        from src.llms.llm import set_model_selection
        set_model_selection(model_provider, model_name)
        logger.info(
            f"[{sanitize_thread_id(thread_id)}] Model selection set: provider={model_provider}, model={model_name}"
        )
    
    safe_thread_id = sanitize_thread_id(thread_id)
    safe_feedback = (
        sanitize_log_input(interrupt_feedback) if interrupt_feedback else ""
    )
    logger.debug(
        f"[{safe_thread_id}] _astream_workflow_generator starting: "
        f"messages_count={len(messages)}, "
        f"auto_accepted_plan={auto_accepted_plan}, "
        f"interrupt_feedback={safe_feedback}, "
        f"interrupt_before_tools={interrupt_before_tools}, "
        f"model_provider={model_provider}, model_name={model_name}"
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
    # FORCE FIX: Ensure pm_agent is in add_to_agents for pm-server
    # This overrides any incorrect frontend configuration
    logger.info(f"[{safe_thread_id}] DEBUG: mcp_settings type={type(mcp_settings)}, value={mcp_settings}")
    if mcp_settings and "servers" in mcp_settings:
        for server_name, server_config in mcp_settings["servers"].items():
            if server_name == "pm-server" or "pm" in server_name.lower():
                current_agents = server_config.get("add_to_agents", [])
                if "pm_agent" not in current_agents:
                    logger.warning(
                        f"[{safe_thread_id}] FORCE FIX: Adding 'pm_agent' to add_to_agents for '{server_name}'. "
                        f"Current: {current_agents}"
                    )
                    server_config["add_to_agents"] = current_agents + ["pm_agent"]
                    logger.info(
                        f"[{safe_thread_id}] FORCE FIX: Updated add_to_agents to {server_config['add_to_agents']}"
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
        # First try direct serialization
        json_data = json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        # If direct serialization fails, use safe serialization
        logger.warning(f"Direct serialization failed for {event_type}, using safe serialize: {e}")
        safe_data = _safe_serialize(data)
        try:
            json_data = json.dumps(safe_data, ensure_ascii=False)
        except (TypeError, ValueError) as e2:
            logger.error(f"Error serializing event data even with safe_serialize: {e2}")
            # Return a safe error event
            error_data = json.dumps(
                {"error": "Serialization failed", "event_type": event_type}, ensure_ascii=False
            )
            return f"event: error\ndata: {error_data}\n\n"

    finish_reason = data.get("finish_reason", "")
    chat_stream_message(
        data.get("thread_id", ""),
        f"event: {event_type}\ndata: {json_data}\n\n",
        finish_reason,
    )

    return f"event: {event_type}\ndata: {json_data}\n\n"


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
        providers=get_available_providers(),
    )

# Project Management Agent API endpoints
# NOTE: Legacy PostgreSQL REST endpoints removed - all PM operations
# now go through /api/pm/chat/stream
# This endpoint uses PM Providers (OpenProject, JIRA, etc.)
# instead of local database


# PM REST endpoints for UI data fetching
@app.get("/api/pm/projects")
async def pm_list_projects(_request: Request):  # FastAPI route parameter, unused
    """List all projects from all active PM providers"""
    try:
        from database.connection import get_db_session
        from src.server.pm_service_client import PMServiceHandler as PMHandler
        
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


@app.post("/api/pm/projects/{project_id}/tasks")
async def pm_create_project_task(project_id: str, payload: PMTaskCreateRequest):
    """Create a new task within the specified project"""
    try:
        from database.connection import get_db_session
        from src.server.pm_service_client import PMServiceHandler as PMHandler

        db_gen = get_db_session()
        db = next(db_gen)

        try:
            handler = PMHandler.from_db_session(db)
            created_task = await handler.create_project_task(
                project_id,
                payload.model_dump(exclude_none=True),
            )
            return created_task
        finally:
            db.close()
    except ValueError as ve:
        error_msg = str(ve)
        import re

        status_match = re.match(r"\((\d{3})\)\s*(.+)", error_msg)
        if status_match:
            status_code = int(status_match.group(1))
            detail = status_match.group(2)
            raise HTTPException(status_code=status_code, detail=detail)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        if "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        if "not yet implemented" in error_msg:
            raise HTTPException(status_code=501, detail=error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/projects/{project_id}/tasks")
async def pm_list_tasks(_request: Request, project_id: str):  # FastAPI route parameter, unused
    """List all tasks for a project"""
    try:
        from src.server.pm_service_client import PMServiceHandler
        
        handler = PMServiceHandler()
        tasks = await handler.list_project_tasks(project_id)
        return tasks
        
    except ValueError as ve:
        error_msg = str(ve)
        import re
        status_match = re.match(r'\((\d{3})\)\s*(.+)', error_msg)
        if status_match:
            status_code = int(status_match.group(1))
            detail = status_match.group(2)
            raise HTTPException(status_code=status_code, detail=detail)
        else:
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


@app.get("/api/pm/projects/{project_id}/timeline")
async def pm_project_timeline(project_id: str):
    """Return sprint + task scheduling data for timeline views."""
    try:
        from database.connection import get_db_session
        from src.server.pm_service_client import PMServiceHandler as PMHandler

        db_gen = get_db_session()
        db = next(db_gen)

        try:
            handler = PMHandler.from_db_session(db)
            timeline = await handler.get_project_timeline(project_id)
            return timeline
        finally:
            db.close()
    except ValueError as ve:
        error_msg = str(ve)
        import re

        status_match = re.match(r"\((\d{3})\)\s*(.+)", error_msg)
        if status_match:
            status_code = int(status_match.group(1))
            detail = status_match.group(2)
            raise HTTPException(status_code=status_code, detail=detail)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        if "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        if "not yet implemented" in error_msg:
            raise HTTPException(status_code=501, detail=error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load project timeline: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/tasks/my")
async def pm_list_my_tasks(_request: Request):  # FastAPI route parameter, unused
    """List tasks assigned to current user across all active PM providers"""
    try:
        from database.connection import get_db_session
        from src.server.pm_service_client import PMServiceHandler as PMHandler
        
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
async def pm_list_all_tasks(_request: Request):  # FastAPI route parameter, unused
    """List all tasks across all projects from all active PM providers"""
    try:
        from database.connection import get_db_session
        from src.server.pm_service_client import PMServiceHandler as PMHandler
        
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
        from src.server.pm_service_client import PMServiceHandler
        
        updates = await request.json()
        
        handler = PMServiceHandler()
        
        # Build composite task_id if needed
        if ":" not in task_id and ":" in project_id:
            provider_id = project_id.split(":")[0]
            composite_task_id = f"{provider_id}:{task_id}"
        else:
            composite_task_id = task_id
        
        logger.info(f"Updating task {composite_task_id} in project {project_id} with updates: {updates}")
        
        # Update the task using PM Service
        updated_task = await handler.update_task(composite_task_id, **updates)
        
        if updated_task:
            logger.info(f"Task {composite_task_id} updated successfully")
            return updated_task
        else:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            
    except ValueError as ve:
        error_msg = str(ve)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        elif "OpenProject API error (422)" in error_msg:
            detail = error_msg.replace("OpenProject API error (422): ", "")
            raise HTTPException(status_code=422, detail=detail)
        elif "OpenProject API error" in error_msg:
            import re
            status_match = re.search(r'\((\d+)\)', error_msg)
            status_code = int(status_match.group(1)) if status_match else 400
            detail = error_msg.split(": ", 1)[1] if ": " in error_msg else error_msg
            raise HTTPException(status_code=status_code, detail=detail)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update task: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/projects/{project_id}/users")
async def pm_list_users(_request: Request, project_id: str):  # FastAPI route parameter, unused
    """List all users for a project"""
    try:
        from src.server.pm_service_client import PMServiceHandler
        
        handler = PMServiceHandler()
        
        try:
            users = await handler.list_project_users(project_id)
            return users
        except Exception as e:
            error_msg = str(e)
            # Handle auth/permission errors gracefully
            if "403" in error_msg or "Forbidden" in error_msg or "401" in error_msg or "Unauthorized" in error_msg:
                logger.warning(f"[pm_list_users] Auth issue, returning empty list: {error_msg}")
                return []
            if "JIRA requires" in error_msg or "username" in error_msg.lower():
                logger.warning(f"[pm_list_users] Config issue, returning empty list: {error_msg}")
                return []
            raise
            
    except ValueError as ve:
        error_msg = str(ve)
        if "JIRA requires" in error_msg or "username" in error_msg.lower():
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
        if "JIRA requires" in error_msg or "username" in error_msg.lower():
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
        from src.server.pm_service_client import PMServiceHandler
        
        handler = PMServiceHandler()
        return await handler.list_project_sprints(project_id, state=state)
        
    except ValueError as ve:
        error_msg = str(ve)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list sprints: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/projects/{project_id}/epics")
async def pm_list_epics(_request: Request, project_id: str):  # FastAPI route parameter, unused
    """List all epics for a project"""
    try:
        from database.connection import get_db_session
        from src.server.pm_service_client import PMServiceHandler as PMHandler
        
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
        from src.server.pm_service_client import PMServiceHandler as PMHandler
        
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
        from src.server.pm_service_client import PMServiceHandler as PMHandler
        
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
        from src.server.pm_service_client import PMServiceHandler as PMHandler
        
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
async def pm_remove_task_from_epic(_request: Request, project_id: str, task_id: str):  # FastAPI route parameter, unused
    """Remove a task from its epic"""
    try:
        from database.connection import get_db_session
        from src.server.pm_service_client import PMServiceHandler as PMHandler
        
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
        from src.server.pm_service_client import PMServiceHandler as PMHandler
        
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


@app.post("/api/pm/projects/{project_id}/tasks/{task_id}/assign-user")
async def pm_assign_task_to_user(project_id: str, task_id: str, payload: TaskAssignmentRequest):
    """Assign or unassign a task to a user"""
    try:
        from database.connection import get_db_session
        from src.server.pm_service_client import PMServiceHandler as PMHandler

        db_gen = get_db_session()
        db = next(db_gen)

        try:
            handler = PMHandler.from_db_session(db)
            return await handler.assign_task_to_user(project_id, task_id, payload.assignee_id)
        finally:
            db.close()
    except ValueError as ve:
        error_msg = str(ve)
        import re

        status_match = re.match(r"\((\d{3})\)\s*(.+)", error_msg)
        if status_match:
            status_code = int(status_match.group(1))
            detail = status_match.group(2)
            raise HTTPException(status_code=status_code, detail=detail)
        if "Invalid provider ID format" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        if "Provider not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        if "not yet implemented" in error_msg:
            raise HTTPException(status_code=501, detail=error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign task: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pm/projects/{project_id}/tasks/{task_id}/move-to-backlog")
async def pm_move_task_to_backlog(_request: Request, project_id: str, task_id: str):  # FastAPI route parameter, unused
    """Move a task to the backlog"""
    try:
        from database.connection import get_db_session
        from src.server.pm_service_client import PMServiceHandler as PMHandler
        
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
async def pm_delete_epic(_request: Request, project_id: str, epic_id: str):  # FastAPI route parameter, unused
    """Delete an epic for a project"""
    try:
        from database.connection import get_db_session
        from src.server.pm_service_client import PMServiceHandler as PMHandler
        
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
async def pm_list_labels(_request: Request, project_id: str):  # FastAPI route parameter, unused
    """List all labels for a project"""
    try:
        from database.connection import get_db_session
        from src.server.pm_service_client import PMServiceHandler as PMHandler
        
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
        from src.server.pm_service_client import PMServiceHandler as PMHandler
        
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
        from src.server.pm_service_client import PMServiceHandler as PMHandler
        
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
    # Check if AI providers are configured
    try:
        from src.llms.llm import has_configured_ai_providers
        if not has_configured_ai_providers():
            error_message = (
                "No AI providers configured. Please configure an AI provider (OpenAI, Anthropic, etc.) "
                "in the Provider Management dialog (AI Providers tab) before using the chat feature."
            )
            logger.warning("[pm_chat_stream] No AI providers configured")
            raise HTTPException(status_code=400, detail=error_message)
    except HTTPException:
        raise
    except Exception as e:
        # If check fails, log but continue (might be using conf.yaml/env vars)
        logger.debug(f"[pm_chat_stream] AI provider check failed (non-fatal): {e}")
    
    # Check if PM providers are configured
    try:
        from src.llms.llm import has_configured_pm_providers
        if not has_configured_pm_providers():
            error_message = (
                "No PM providers configured. Please configure a project management provider (OpenProject, JIRA, etc.) "
                "in the Provider Management dialog (PM Providers tab) before using the chat feature."
            )
            logger.warning("[pm_chat_stream] No PM providers configured")
            raise HTTPException(status_code=400, detail=error_message)
    except HTTPException:
        raise
    except Exception as e:
        # If check fails, log but continue (might have providers configured elsewhere)
        logger.debug(f"[pm_chat_stream] PM provider check failed (non-fatal): {e}")
    
    try:
        from src.conversation.flow_manager import ConversationFlowManager
        from src.memory import get_conversation_memory
        from database.connection import get_db_session
        import uuid
        import time
            
        body = await request.json()
        
        # Extract messages - support both single message and conversation history
        raw_messages = body.get("messages", [{}])
        user_message = raw_messages[-1].get("content", "") if raw_messages else ""
        
        # Extract conversation history (all messages except the last one)
        conversation_history = body.get("conversation_history", [])
        if not conversation_history and len(raw_messages) > 1:
            # If no explicit history, use messages array (excluding last)
            conversation_history = raw_messages[:-1]
        
        # Extract model selection from request
        model_provider = body.get("model_provider")
        model_name = body.get("model_name")
        
        thread_id = body.get("thread_id", str(uuid.uuid4()))
        
        logger.info(f"[PM-CHAT] Received message with {len(conversation_history)} history messages")
        
        # Get or create conversation memory for this thread
        # This provides persistent storage and semantic retrieval
        memory = get_conversation_memory(
            thread_id,
            short_term_limit=10,
            enable_vector_store=False,  # Disable for now to avoid OpenAI API calls
            enable_summarization=False,  # Disable for now
        )
        
        # Add user message to memory
        memory.add_message("user", user_message)
            
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
                            # ReportStyle already imported at top of file
                                
                            # Use default MCP settings to ensure PM tools are available
                            pm_mcp_settings = get_default_mcp_settings()
                            logger.info(f"[PM-CHAT] Using default MCP settings with servers: {list(pm_mcp_settings.get('servers', {}).keys())}")
                            
                            # Build messages with conversation history for context
                            workflow_messages = []
                            
                            # Add conversation history for context continuity
                            if conversation_history:
                                for hist_msg in conversation_history[-10:]:  # Last 10 messages
                                    workflow_messages.append({
                                        "role": hist_msg.get("role", "user"),
                                        "content": hist_msg.get("content", "")
                                    })
                                logger.info(f"[PM-CHAT] Added {len(workflow_messages)} history messages to context")
                            
                            # Add current user message
                            workflow_messages.append({"role": "user", "content": research_query})
                            
                            async for event in _astream_workflow_generator(
                                messages=workflow_messages,
                                thread_id=thread_id,
                                resources=[],
                                max_plan_iterations=1,
                                max_step_num=3,
                                max_search_results=3,
                                auto_accepted_plan=True,
                                interrupt_feedback="",
                                mcp_settings=pm_mcp_settings,
                                enable_background_investigation=True,
                                report_style=ReportStyle.ACADEMIC,
                                enable_deep_thinking=False,
                                enable_clarification=False,
                                max_clarification_rounds=3,
                                locale="en-US",
                                interrupt_before_tools=None,
                                model_provider=model_provider,
                                model_name=model_name,
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
                                # datetime already imported at top of file
                                    
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
        from src.server.mcp_sync import get_mcp_provider_id
        
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
                    # Include MCP provider ID for AI Agent context
                    "mcp_provider_id": get_mcp_provider_id(p),
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
        from src.server.mcp_sync import sync_provider_to_mcp, MCPSyncError, set_mcp_provider_id
        
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
            
            # Sync provider to MCP Server
            mcp_sync_result = None
            mcp_sync_error = None
            try:
                mcp_sync_result = await sync_provider_to_mcp(
                    backend_provider_id=str(provider.id),
                    name=str(provider.name),
                    provider_type=str(provider.provider_type),
                    base_url=str(provider.base_url),
                    api_key=request.api_key,
                    api_token=request.api_token,
                    username=request.username,
                    organization_id=request.organization_id,
                    workspace_id=request.workspace_id,
                    is_active=True,
                    test_connection=False,  # We'll test below
                )
                # Store MCP provider ID in additional_config
                if mcp_sync_result and mcp_sync_result.get("success"):
                    set_mcp_provider_id(provider, mcp_sync_result["mcp_provider_id"])
                    db.commit()
                    logger.info(f"[pm_import_projects] Provider synced to MCP: {mcp_sync_result}")
            except MCPSyncError as e:
                mcp_sync_error = str(e)
                logger.warning(f"[pm_import_projects] MCP sync failed (non-fatal): {e}")
            
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
            
            # Build response with MCP sync info
            response = {
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
                "errors": [],
                "mcp_sync": {
                    "success": mcp_sync_result.get("success") if mcp_sync_result else False,
                    "mcp_provider_id": mcp_sync_result.get("mcp_provider_id") if mcp_sync_result else None,
                    "error": mcp_sync_error,
                }
            }
            return response
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
                import traceback
                logger.error(
                    f"Failed to fetch projects from provider {provider_id} "
                    f"({provider.provider_type}): {error_msg}"
                )
                logger.error(traceback.format_exc())
                
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
        from src.server.mcp_sync import sync_provider_to_mcp, MCPSyncError, set_mcp_provider_id
        
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
            
            # Sync updated provider to MCP Server
            # This is critical for keeping credentials in sync (e.g., after token refresh)
            mcp_sync_result = None
            mcp_sync_error = None
            try:
                mcp_sync_result = await sync_provider_to_mcp(
                    backend_provider_id=str(provider.id),
                    name=str(provider.name),
                    provider_type=str(provider.provider_type),
                    base_url=str(provider.base_url),
                    api_key=str(provider.api_key) if provider.api_key else None,
                    api_token=str(provider.api_token) if provider.api_token else None,
                    username=str(provider.username) if provider.username else None,
                    organization_id=str(provider.organization_id) if provider.organization_id else None,
                    workspace_id=str(provider.workspace_id) if provider.workspace_id else None,
                    is_active=bool(provider.is_active),
                    test_connection=False,
                )
                # Update MCP provider ID if sync succeeded
                if mcp_sync_result and mcp_sync_result.get("success"):
                    set_mcp_provider_id(provider, mcp_sync_result["mcp_provider_id"])
                    db.commit()
                    logger.info(f"[pm_update_provider] Provider synced to MCP: {mcp_sync_result}")
            except MCPSyncError as e:
                mcp_sync_error = str(e)
                logger.warning(f"[pm_update_provider] MCP sync failed (non-fatal): {e}")
            
            return {
                "id": str(provider.id),
                "name": provider.name,
                "provider_type": provider.provider_type,
                "base_url": provider.base_url,
                "username": provider.username,
                "organization_id": provider.organization_id,
                "workspace_id": provider.workspace_id,
                "mcp_sync": {
                    "success": mcp_sync_result.get("success") if mcp_sync_result else False,
                    "mcp_provider_id": mcp_sync_result.get("mcp_provider_id") if mcp_sync_result else None,
                    "error": mcp_sync_error,
                }
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


@app.post("/api/pm/providers/{provider_id}/sync")
async def pm_sync_provider_to_mcp(provider_id: str):
    """
    Manually sync a provider to MCP Server.
    
    Use this when:
    - Provider credentials were updated outside the normal flow
    - MCP Server was down during a previous sync
    - Token expired and was refreshed manually
    """
    try:
        from database.connection import get_db_session
        from database.orm_models import PMProviderConnection
        from src.server.mcp_sync import sync_provider_to_mcp, MCPSyncError, set_mcp_provider_id
        
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
            
            # Sync to MCP Server
            mcp_sync_result = await sync_provider_to_mcp(
                backend_provider_id=str(provider.id),
                name=str(provider.name),
                provider_type=str(provider.provider_type),
                base_url=str(provider.base_url),
                api_key=str(provider.api_key) if provider.api_key else None,
                api_token=str(provider.api_token) if provider.api_token else None,
                username=str(provider.username) if provider.username else None,
                organization_id=str(provider.organization_id) if provider.organization_id else None,
                workspace_id=str(provider.workspace_id) if provider.workspace_id else None,
                is_active=bool(provider.is_active),
                test_connection=True,  # Test connection on manual sync
            )
            
            # Update MCP provider ID
            if mcp_sync_result and mcp_sync_result.get("success"):
                set_mcp_provider_id(provider, mcp_sync_result["mcp_provider_id"])
                db.commit()
            
            return {
                "success": True,
                "provider_id": str(provider.id),
                "mcp_sync": mcp_sync_result,
            }
        finally:
            db.close()
    except MCPSyncError as e:
        logger.error(f"MCP sync failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pm/providers/sync-all")
async def pm_sync_all_providers_to_mcp():
    """
    Sync all active providers to MCP Server.
    
    Use this for:
    - Initial setup after MCP Server deployment
    - Periodic reconciliation
    - Recovery after MCP Server restart
    """
    try:
        from database.connection import get_db_session
        from database.orm_models import PMProviderConnection
        from src.server.mcp_sync import bulk_sync_providers_to_mcp, MCPSyncError, set_mcp_provider_id
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            # Get all active providers
            providers = db.query(PMProviderConnection).filter(
                PMProviderConnection.is_active.is_(True)
            ).all()
            
            if not providers:
                return {
                    "success": True,
                    "message": "No active providers to sync",
                    "synced": 0,
                    "failed": 0,
                }
            
            # Build sync requests
            sync_requests = []
            for provider in providers:
                sync_requests.append({
                    "backend_provider_id": str(provider.id),
                    "name": str(provider.name),
                    "provider_type": str(provider.provider_type),
                    "base_url": str(provider.base_url),
                    "api_key": provider.api_key,
                    "api_token": provider.api_token,
                    "username": str(provider.username) if provider.username else None,
                    "organization_id": str(provider.organization_id) if provider.organization_id else None,
                    "workspace_id": str(provider.workspace_id) if provider.workspace_id else None,
                    "is_active": bool(provider.is_active),
                    "test_connection": False,  # Skip connection test for bulk sync
                })
            
            # Bulk sync
            result = await bulk_sync_providers_to_mcp(
                providers=sync_requests,
                delete_missing=False,  # Don't delete orphaned MCP providers
            )
            
            # Update MCP provider IDs for successful syncs
            for sync_result in result.get("results", []):
                if sync_result.get("success") and sync_result.get("mcp_provider_id"):
                    backend_id = sync_result.get("backend_provider_id")
                    for provider in providers:
                        if str(provider.id) == backend_id:
                            set_mcp_provider_id(provider, sync_result["mcp_provider_id"])
                            break
            
            db.commit()
            
            return {
                "success": result.get("success", False),
                "message": f"Synced {result.get('synced', 0)} of {len(providers)} providers",
                "total": len(providers),
                "synced": result.get("synced", 0),
                "failed": result.get("failed", 0),
                "errors": result.get("errors", []),
            }
        finally:
            db.close()
    except MCPSyncError as e:
        logger.error(f"Bulk MCP sync failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to sync providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pm/providers/check-sync")
async def pm_check_and_sync_providers():
    """
    Check all providers and sync any that are out of sync with MCP Server.
    
    This endpoint:
    1. Checks each provider's connection health in MCP Server
    2. Re-syncs any providers that have connection issues
    3. Reports which providers are healthy/unhealthy
    
    Use this for:
    - Manual health check
    - After token refresh
    - Troubleshooting sync issues
    """
    try:
        from src.server.mcp_sync import check_and_sync_providers
        
        result = await check_and_sync_providers()
        return result
        
    except Exception as e:
        logger.error(f"Failed to check and sync providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pm/providers/sync-status")
async def pm_get_sync_status():
    """
    Get the sync status between Backend and MCP Server.
    
    Shows which providers are synced and which need attention.
    """
    try:
        from database.connection import get_db_session
        from database.orm_models import PMProviderConnection
        from src.server.mcp_sync import get_mcp_sync_status, get_mcp_provider_id
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            # Get Backend providers
            backend_providers = db.query(PMProviderConnection).all()
            
            # Get MCP Server status
            mcp_status = await get_mcp_sync_status()
            
            # Build comparison
            backend_list = []
            for provider in backend_providers:
                mcp_id = get_mcp_provider_id(provider)
                backend_list.append({
                    "backend_provider_id": str(provider.id),
                    "mcp_provider_id": mcp_id,
                    "name": provider.name,
                    "provider_type": provider.provider_type,
                    "base_url": provider.base_url,
                    "is_active": provider.is_active,
                    "synced": bool(mcp_id),
                })
            
            return {
                "backend": {
                    "total": len(backend_providers),
                    "active": sum(1 for p in backend_providers if p.is_active),
                    "synced": sum(1 for p in backend_list if p["synced"]),
                    "providers": backend_list,
                },
                "mcp_server": mcp_status,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/pm/providers/{provider_id}")
async def pm_delete_provider(provider_id: str):
    """Delete (deactivate) a provider"""
    try:
        from database.connection import get_db_session
        from database.orm_models import PMProviderConnection
        from src.server.mcp_sync import delete_provider_from_mcp, MCPSyncError
        
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
            
            # Sync deletion to MCP Server
            mcp_sync_result = None
            mcp_sync_error = None
            try:
                mcp_sync_result = await delete_provider_from_mcp(
                    backend_provider_id=str(provider.id),
                    hard_delete=False,  # Just deactivate, don't hard delete
                )
                logger.info(f"[pm_delete_provider] Provider deleted from MCP: {mcp_sync_result}")
            except MCPSyncError as e:
                mcp_sync_error = str(e)
                logger.warning(f"[pm_delete_provider] MCP sync failed (non-fatal): {e}")
            
            return {
                "success": True,
                "message": "Provider deactivated",
                "mcp_sync": {
                    "success": mcp_sync_result.get("success") if mcp_sync_result else False,
                    "action": mcp_sync_result.get("action") if mcp_sync_result else None,
                    "error": mcp_sync_error,
                }
            }
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AI Provider API Key Management Endpoints
# ============================================================================

@app.get("/api/ai/providers", response_model=List[AIProviderAPIKeyResponse])
async def list_ai_providers():
    """List all configured AI provider API keys"""
    try:
        from database.connection import get_db_session
        from database.orm_models import AIProviderAPIKey
        
        logger.info("[list_ai_providers] Starting to fetch AI providers from database")
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            logger.debug("[list_ai_providers] Database session obtained, querying providers")
            providers = db.query(AIProviderAPIKey).filter(
                AIProviderAPIKey.is_active.is_(True)
            ).all()
            
            logger.info(f"[list_ai_providers] Found {len(providers)} active AI providers")
            result = []
            for p in providers:
                # Mask API key - show only last 4 characters
                masked_key = None
                api_key_str = str(p.api_key) if p.api_key else None
                has_key = bool(api_key_str)
                if api_key_str and len(api_key_str) > 4:
                    masked_key = f"****{api_key_str[-4:]}"
                elif api_key_str:
                    masked_key = "****"
                
                result.append(AIProviderAPIKeyResponse(
                    id=str(p.id),
                    provider_id=str(p.provider_id),
                    provider_name=str(p.provider_name),
                    api_key=masked_key,
                    base_url=str(p.base_url) if p.base_url else None,
                    model_name=str(p.model_name) if p.model_name else None,
                    additional_config=p.additional_config if p.additional_config else None,
                    is_active=bool(p.is_active),
                    has_api_key=has_key,
                    created_at=p.created_at.isoformat() if p.created_at else "",
                    updated_at=p.updated_at.isoformat() if p.updated_at else "",
                ))
            
            logger.info(f"[list_ai_providers] Returning {len(result)} providers")
            return result
        finally:
            db.close()
            logger.debug("[list_ai_providers] Database session closed")
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Failed to list AI providers: {e}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Failed to list AI providers: {str(e)}")


@app.post("/api/ai/providers", response_model=AIProviderAPIKeyResponse)
async def save_ai_provider(request: AIProviderAPIKeyRequest):
    """Save or update an AI provider API key"""
    try:
        from database.connection import get_db_session
        from database.orm_models import AIProviderAPIKey
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            # Check if provider already exists
            existing = db.query(AIProviderAPIKey).filter(
                AIProviderAPIKey.provider_id == request.provider_id
            ).first()
            
            if existing:
                # Update existing
                existing.provider_name = request.provider_name  # type: ignore[assignment]
                if request.api_key:
                    existing.api_key = request.api_key  # type: ignore[assignment]
                existing.base_url = request.base_url  # type: ignore[assignment]
                existing.model_name = request.model_name  # type: ignore[assignment]
                existing.additional_config = request.additional_config  # type: ignore[assignment]
                existing.is_active = request.is_active  # type: ignore[assignment]
                existing.updated_at = datetime.utcnow()  # type: ignore[assignment]
                db.commit()
                db.refresh(existing)
                provider = existing
            else:
                # Create new
                provider = AIProviderAPIKey(
                    provider_id=request.provider_id,
                    provider_name=request.provider_name,
                    api_key=request.api_key,
                    base_url=request.base_url,
                    model_name=request.model_name,
                    additional_config=request.additional_config,
                    is_active=request.is_active,
                )
                db.add(provider)
                db.commit()
                db.refresh(provider)
            
            # Mask API key for response
            masked_key = None
            api_key_str = str(provider.api_key) if provider.api_key else None
            has_key = bool(api_key_str)
            if api_key_str and len(api_key_str) > 4:
                masked_key = f"****{api_key_str[-4:]}"
            elif api_key_str:
                masked_key = "****"
            
            return AIProviderAPIKeyResponse(
                id=str(provider.id),
                provider_id=str(provider.provider_id),
                provider_name=str(provider.provider_name),
                api_key=masked_key,
                base_url=str(provider.base_url) if provider.base_url else None,
                model_name=str(provider.model_name) if provider.model_name else None,
                additional_config=provider.additional_config if provider.additional_config else None,
                is_active=bool(provider.is_active),
                has_api_key=has_key,
                created_at=provider.created_at.isoformat() if provider.created_at else "",
                updated_at=provider.updated_at.isoformat() if provider.updated_at else "",
            )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to save AI provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/ai/providers/{provider_id}")
async def delete_ai_provider(provider_id: str):
    """Delete (deactivate) an AI provider API key"""
    try:
        from database.connection import get_db_session
        from database.orm_models import AIProviderAPIKey
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            provider = db.query(AIProviderAPIKey).filter(
                AIProviderAPIKey.provider_id == provider_id
            ).first()
            
            if not provider:
                raise HTTPException(
                    status_code=404, detail="AI provider not found"
                )
            
            # Soft delete by deactivating
            provider.is_active = False  # type: ignore
            db.commit()
            
            return {"success": True, "message": "AI provider deactivated"}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete AI provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Search Provider Endpoints
# ============================================================================

@app.get("/api/search/providers", response_model=List[SearchProviderAPIKeyResponse])
async def list_search_providers():
    """List all configured search provider API keys"""
    try:
        from database.connection import get_db_session
        from database.orm_models import SearchProviderAPIKey
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            providers = db.query(SearchProviderAPIKey).filter(
                SearchProviderAPIKey.is_active.is_(True)
            ).all()
            
            result = []
            for p in providers:
                # Mask API key - show only last 4 characters
                masked_key = None
                api_key_str = str(p.api_key) if p.api_key else None
                has_key = bool(api_key_str)
                if api_key_str and len(api_key_str) > 4:
                    masked_key = f"****{api_key_str[-4:]}"
                elif api_key_str:
                    masked_key = "****"
                
                result.append(SearchProviderAPIKeyResponse(
                    id=str(p.id),
                    provider_id=str(p.provider_id),
                    provider_name=str(p.provider_name),
                    api_key=masked_key,
                    base_url=str(p.base_url) if p.base_url else None,
                    additional_config=p.additional_config if p.additional_config else None,
                    is_active=bool(p.is_active),
                    is_default=bool(p.is_default),
                    has_api_key=has_key,
                    created_at=p.created_at.isoformat() if p.created_at else "",
                    updated_at=p.updated_at.isoformat() if p.updated_at else "",
                ))
            
            return result
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to list search providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search/providers", response_model=SearchProviderAPIKeyResponse)
async def save_search_provider(request: SearchProviderAPIKeyRequest):
    """Save or update a search provider API key"""
    try:
        from database.connection import get_db_session
        from database.orm_models import SearchProviderAPIKey
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            # If setting as default, unset other defaults first
            if request.is_default:
                db.query(SearchProviderAPIKey).filter(
                    SearchProviderAPIKey.is_default.is_(True)
                ).update({"is_default": False})
                db.commit()
            
            # Check if provider already exists
            existing = db.query(SearchProviderAPIKey).filter(
                SearchProviderAPIKey.provider_id == request.provider_id
            ).first()
            
            if existing:
                # Update existing
                existing.provider_name = request.provider_name  # type: ignore[assignment]
                if request.api_key:
                    existing.api_key = request.api_key  # type: ignore[assignment]
                existing.base_url = request.base_url  # type: ignore[assignment]
                existing.additional_config = request.additional_config  # type: ignore[assignment]
                existing.is_active = request.is_active  # type: ignore[assignment]
                existing.is_default = request.is_default  # type: ignore[assignment]
                existing.updated_at = datetime.utcnow()  # type: ignore[assignment]
                db.commit()
                db.refresh(existing)
                provider = existing
            else:
                # Create new
                provider = SearchProviderAPIKey(
                    provider_id=request.provider_id,
                    provider_name=request.provider_name,
                    api_key=request.api_key,
                    base_url=request.base_url,
                    additional_config=request.additional_config,
                    is_active=request.is_active,
                    is_default=request.is_default,
                )
                db.add(provider)
                db.commit()
                db.refresh(provider)
            
            # Mask API key for response
            masked_key = None
            api_key_str = str(provider.api_key) if provider.api_key else None
            has_key = bool(api_key_str)
            if api_key_str and len(api_key_str) > 4:
                masked_key = f"****{api_key_str[-4:]}"
            elif api_key_str:
                masked_key = "****"
            
            return SearchProviderAPIKeyResponse(
                id=str(provider.id),
                provider_id=str(provider.provider_id),
                provider_name=str(provider.provider_name),
                api_key=masked_key,
                base_url=str(provider.base_url) if provider.base_url else None,
                additional_config=provider.additional_config if provider.additional_config else None,
                is_active=bool(provider.is_active),
                is_default=bool(provider.is_default),
                has_api_key=has_key,
                created_at=provider.created_at.isoformat() if provider.created_at else "",
                updated_at=provider.updated_at.isoformat() if provider.updated_at else "",
            )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to save search provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search/providers/test-connection")
async def test_search_provider_connection(request: SearchProviderAPIKeyRequest):
    """Test connection to a search provider by making a test search"""
    try:
        from src.tools.search import get_web_search_tool
        from src.config import SearchEngine
        
        # Check if provider needs API key
        needs_api_key = request.provider_id in [
            SearchEngine.TAVILY.value,
            "tavily",
            SearchEngine.BRAVE_SEARCH.value,
            "brave_search",
        ]
        
        # Check if API key is required and provided
        if needs_api_key and not request.api_key:
            return {
                "success": False,
                "message": f"API key is required for {request.provider_name}"
            }
        
        # For Searx, check if base_url is provided
        if request.provider_id in [SearchEngine.SEARX.value, "searx"]:
            if not request.base_url:
                return {
                    "success": False,
                    "message": "Base URL is required for Searx"
                }
        
        # Create a temporary search tool with the provided credentials
        # We'll temporarily set environment variables or pass credentials directly
        import os
        original_env = {}
        
        try:
            # Set environment variables temporarily for testing
            if request.provider_id in [SearchEngine.TAVILY.value, "tavily"]:
                if request.api_key:
                    original_env["TAVILY_API_KEY"] = os.environ.get("TAVILY_API_KEY")
                    os.environ["TAVILY_API_KEY"] = request.api_key
            elif request.provider_id in [SearchEngine.BRAVE_SEARCH.value, "brave_search"]:
                if request.api_key:
                    original_env["BRAVE_SEARCH_API_KEY"] = os.environ.get("BRAVE_SEARCH_API_KEY")
                    os.environ["BRAVE_SEARCH_API_KEY"] = request.api_key
            
            # Get search tool with test credentials
            # We need to create the tool directly with the provided credentials
            test_query = "test"
            
            if request.provider_id in [SearchEngine.TAVILY.value, "tavily"]:
                from src.tools.tavily_search.tavily_search_results_with_images import TavilySearchWithImages
                from src.tools.tavily_search.tavily_search_api_wrapper import EnhancedTavilySearchAPIWrapper
                
                if not request.api_key:
                    return {
                        "success": False,
                        "message": "API key is required for Tavily"
                    }
                
                # Create Tavily wrapper with API key
                api_wrapper = EnhancedTavilySearchAPIWrapper(tavily_api_key=request.api_key)
                search_tool = TavilySearchWithImages(
                    name="web_search",
                    max_results=1,
                    api_wrapper=api_wrapper
                )
                
                # Test with a simple query
                result = search_tool.invoke(test_query)
                if isinstance(result, tuple):
                    result = result[0]
                
                # Check if result contains error
                if isinstance(result, str):
                    try:
                        import json
                        parsed = json.loads(result)
                        if isinstance(parsed, dict) and "error" in parsed:
                            return {
                                "success": False,
                                "message": f"Tavily API error: {parsed.get('error', 'Unknown error')}"
                            }
                    except json.JSONDecodeError:
                        pass  # Not JSON, assume success
                
            elif request.provider_id in [SearchEngine.BRAVE_SEARCH.value, "brave_search"]:
                from src.tools.search import BraveSearch
                
                if not request.api_key:
                    return {
                        "success": False,
                        "message": "API key is required for Brave Search"
                    }
                
                search_tool = BraveSearch(api_key=request.api_key)
                result = search_tool.invoke(test_query)
                
                # Check for errors
                if isinstance(result, str) and "ERROR" in result:
                    return {
                        "success": False,
                        "message": result
                    }
                    
            elif request.provider_id in [SearchEngine.SEARX.value, "searx"]:
                from src.tools.search import SearxSearchRun, SearxSearchWrapper
                
                if not request.base_url:
                    return {
                        "success": False,
                        "message": "Base URL is required for Searx"
                    }
                
                wrapper = SearxSearchWrapper(k=1, base_url=request.base_url)
                search_tool = SearxSearchRun(wrapper=wrapper)
                result = search_tool.invoke(test_query)
                
                # Check for errors
                if isinstance(result, str) and "ERROR" in result:
                    return {
                        "success": False,
                        "message": result
                    }
                    
            elif request.provider_id in [SearchEngine.DUCKDUCKGO.value, "duckduckgo"]:
                # DuckDuckGo doesn't need API key, just test that it works
                from src.tools.search import DuckDuckGoSearchResults
                search_tool = DuckDuckGoSearchResults(num_results=1)
                result = search_tool.invoke(test_query)
                
            else:
                return {
                    "success": False,
                    "message": f"Unsupported search provider: {request.provider_id}"
                }
            
            return {
                "success": True,
                "message": f"Connection successful. {request.provider_name} API key is valid."
            }
            
        finally:
            # Restore original environment variables
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
                    
    except Exception as e:
        logger.error(f"Search provider connection test failed: {e}", exc_info=True)
        error_message = str(e)
        
        # Provide more user-friendly error messages
        if "api_key" in error_message.lower() or "authentication" in error_message.lower():
            error_message = "Authentication failed. Please check your API key."
        elif "connection" in error_message.lower() or "timeout" in error_message.lower():
            error_message = "Connection failed. Please check your network connection and base URL."
        elif "not found" in error_message.lower() or "404" in error_message:
            error_message = "Service not found. Please check your base URL."
        
        return {
            "success": False,
            "message": f"Connection test failed: {error_message}"
        }


@app.delete("/api/search/providers/{provider_id}")
async def delete_search_provider(provider_id: str):
    """Delete (deactivate) a search provider API key"""
    try:
        from database.connection import get_db_session
        from database.orm_models import SearchProviderAPIKey
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            provider = db.query(SearchProviderAPIKey).filter(
                SearchProviderAPIKey.provider_id == provider_id
            ).first()
            
            if not provider:
                raise HTTPException(
                    status_code=404, detail="Search provider not found"
                )
            
            # Soft delete by deactivating
            provider.is_active = False  # type: ignore
            provider.is_default = False  # type: ignore
            db.commit()
            
            return {"success": True, "message": "Search provider deactivated"}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete search provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Analytics Endpoints
# ============================================================================

from src.analytics.service import AnalyticsService
from src.analytics.adapters.pm_adapter import PMProviderAnalyticsAdapter
from database.orm_models import PMProviderConnection
from pm_providers.factory import create_pm_provider


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
        
        # Create provider instance directly using factory
        provider_instance = create_pm_provider(
            provider_type=provider_conn.provider_type,
            base_url=provider_conn.base_url,
            api_key=provider_conn.api_key,
            api_token=provider_conn.api_token,
            username=provider_conn.username,
            organization_id=provider_conn.organization_id,
            workspace_id=provider_conn.workspace_id
        )
        
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
    logger.info(f"[get_burndown_chart] ========== BURNDOWN REQUEST START ==========")
    logger.info(f"[get_burndown_chart] project_id={project_id}, sprint_id={sprint_id}, scope_type={scope_type}")
    try:
        from database.connection import get_db_session
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            analytics_service = get_analytics_service(project_id, db)
            # Extract actual project ID if in provider_id:project_id format
            actual_project_id = (
                project_id.split(":", 1)[1]
                if ":" in project_id
                else project_id
            )
            logger.info(f"[get_burndown_chart] Using actual_project_id={actual_project_id}, sprint_id={sprint_id}")
            chart = await analytics_service.get_burndown_chart(
                project_id=actual_project_id,
                sprint_id=sprint_id,
                scope_type=scope_type  # type: ignore
            )
            logger.info(f"[get_burndown_chart] Success: returning chart data")
            return chart.model_dump()
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    except Exception as e:
        logger.error(f"Failed to get burndown chart: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
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
            # Extract actual project ID if in provider_id:project_id format
            actual_project_id = (
                project_id.split(":", 1)[1]
                if ":" in project_id
                else project_id
            )
            chart = await analytics_service.get_velocity_chart(
                project_id=actual_project_id,
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
            # Extract actual project ID if in provider_id:project_id format
            actual_project_id = (
                project_id.split(":", 1)[1]
                if ":" in project_id
                else project_id
            )
            report = await analytics_service.get_sprint_report(sprint_id=sprint_id, project_id=actual_project_id)
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
            # Extract actual project ID if in provider_id:project_id format
            actual_project_id = (
                project_id.split(":", 1)[1]
                if ":" in project_id
                else project_id
            )
            summary = await analytics_service.get_project_summary(project_id=actual_project_id)
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
            # Extract actual project ID if in provider_id:project_id format
            actual_project_id = (
                project_id.split(":", 1)[1]
                if ":" in project_id
                else project_id
            )
            chart = await analytics_service.get_cfd_chart(project_id=actual_project_id, sprint_id=sprint_id, days_back=days_back)
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
        import traceback
        logger.error(traceback.format_exc())
        error_detail = str(e)
        raise HTTPException(status_code=500, detail=error_detail)


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
            # Extract actual project ID if in provider_id:project_id format
            actual_project_id = (
                project_id.split(":", 1)[1]
                if ":" in project_id
                else project_id
            )
            chart = await analytics_service.get_cycle_time_chart(project_id=actual_project_id, sprint_id=sprint_id, days_back=days_back)
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
            # Extract actual project ID if in provider_id:project_id format
            actual_project_id = (
                project_id.split(":", 1)[1]
                if ":" in project_id
                else project_id
            )
            chart = await analytics_service.get_work_distribution_chart(project_id=actual_project_id, dimension=dimension, sprint_id=sprint_id)
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
            # Extract actual project ID if in provider_id:project_id format
            actual_project_id = (
                project_id.split(":", 1)[1]
                if ":" in project_id
                else project_id
            )
            chart = await analytics_service.get_issue_trend_chart(project_id=actual_project_id, days_back=days_back, sprint_id=sprint_id)
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
            # Extract actual project ID if in provider_id:project_id format
            actual_project_id = (
                project_id.split(":", 1)[1]
                if ":" in project_id
                else project_id
            )
            chart = await analytics_service.get_work_distribution_chart(project_id=actual_project_id, dimension=dimension, sprint_id=sprint_id)
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
            # Extract actual project ID if in provider_id:project_id format
            actual_project_id = (
                project_id.split(":", 1)[1]
                if ":" in project_id
                else project_id
            )
            chart = await analytics_service.get_issue_trend_chart(project_id=actual_project_id, days_back=days_back, sprint_id=sprint_id)
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
