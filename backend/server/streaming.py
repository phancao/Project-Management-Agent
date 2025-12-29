# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Streaming Module

Handles all event streaming logic for the chat API.
Extracted from app.py for better separation of concerns and testability.
"""

import json
import logging
from typing import Any, AsyncIterator, Optional
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from backend.graph.checkpoint import chat_stream_message
from backend.utils.json_utils import sanitize_args
from backend.utils.log_sanitizer import (
    sanitize_agent_name,
    sanitize_log_input,
    sanitize_thread_id,
    sanitize_tool_name,
)

logger = logging.getLogger(__name__)

# Cache to store react_thoughts by message ID for AIMessageChunk processing
# This is needed because AIMessageChunk is streamed before the final AIMessage
_react_thoughts_cache: dict[str, list] = {}


def clear_thoughts_cache():
    """Clear the react_thoughts cache."""
    global _react_thoughts_cache
    _react_thoughts_cache = {}


def cache_thoughts(message_id: str, thoughts: list):
    """Cache react_thoughts for a message ID."""
    if message_id and thoughts:
        _react_thoughts_cache[message_id] = thoughts


def get_cached_thoughts(message_id: str) -> Optional[list]:
    """Get cached react_thoughts for a message ID."""
    return _react_thoughts_cache.get(message_id)


def make_event(event_type: str, data: dict[str, Any]) -> str:
    """Create a Server-Sent Event string."""
    if data.get("content") == "":
        data.pop("content")
    
    try:
        json_data = json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        logger.warning(f"Direct serialization failed for {event_type}: {e}")
        safe_data = safe_serialize(data)
        try:
            json_data = json.dumps(safe_data, ensure_ascii=False)
        except (TypeError, ValueError) as e2:
            logger.error(f"Error serializing event data: {e2}")
            error_data = json.dumps(
                {"error": "Serialization failed", "event_type": event_type},
                ensure_ascii=False
            )
            return f"event: error\ndata: {error_data}\n\n"

    finish_reason = data.get("finish_reason", "")
    chat_stream_message(
        data.get("thread_id", ""),
        f"event: {event_type}\ndata: {json_data}\n\n",
        finish_reason,
    )
    return f"event: {event_type}\ndata: {json_data}\n\n"


def safe_serialize(obj: Any) -> Any:
    """Safely serialize an object to JSON-compatible format."""
    if isinstance(obj, str):
        return obj
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        if isinstance(obj, dict):
            return {k: safe_serialize(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [safe_serialize(item) for item in obj]
        else:
            return str(obj)


def get_agent_name(agent: tuple, message_metadata: dict, message_chunk: Any = None) -> str:
    """Extract agent name from agent tuple, metadata, or message."""
    agent_name = "unknown"
    
    # Priority 1: Check message.name attribute
    if message_chunk and hasattr(message_chunk, 'name') and message_chunk.name:
        agent_name = message_chunk.name
    # Priority 2: Check agent tuple from LangGraph
    elif agent and len(agent) > 0:
        agent_name = agent[0].split(":")[0] if ":" in agent[0] else agent[0]
    # Priority 3: Check message metadata
    else:
        agent_name = message_metadata.get("langgraph_node", "unknown")
    
    return agent_name


def validate_tool_call_chunks(tool_call_chunks: list) -> None:
    """Validate tool call chunk structure for debugging."""
    if not tool_call_chunks:
        return
    
    
    indices_seen = set()
    for i, chunk in enumerate(tool_call_chunks):
        index = chunk.get("index")
        if index is not None:
            indices_seen.add(index)
    
    if len(indices_seen) > 1:
        pass


def process_tool_call_chunks(tool_call_chunks: list) -> list:
    """
    Process tool call chunks with proper index-based grouping.
    
    Groups chunks by index and accumulates arguments for streaming tool calls.
    """
    if not tool_call_chunks:
        return []
    
    validate_tool_call_chunks(tool_call_chunks)
    
    chunks = []
    chunk_by_index = {}
    
    for chunk in tool_call_chunks:
        index = chunk.get("index")
        chunk_id = chunk.get("id")
        
        if index is not None:
            if index not in chunk_by_index:
                chunk_by_index[index] = {
                    "name": "",
                    "args": "",
                    "id": chunk_id or "",
                    "index": index,
                    "type": chunk.get("type", ""),
                }
            
            chunk_name = chunk.get("name", "")
            if chunk_name:
                stored_name = chunk_by_index[index]["name"]
                if stored_name and stored_name != chunk_name:
                    logger.warning(
                        f"Tool name mismatch at index {index}: "
                        f"'{stored_name}' != '{chunk_name}'"
                    )
                else:
                    chunk_by_index[index]["name"] = chunk_name
            
            if chunk_id and not chunk_by_index[index]["id"]:
                chunk_by_index[index]["id"] = chunk_id
            
            if chunk.get("args"):
                chunk_by_index[index]["args"] += chunk.get("args", "")
        else:
            chunks.append({
                "name": chunk.get("name", ""),
                "args": sanitize_args(chunk.get("args", "")),
                "id": chunk.get("id", ""),
                "index": 0,
                "type": chunk.get("type", ""),
            })
    
    for index in sorted(chunk_by_index.keys()):
        chunk_data = chunk_by_index[index]
        chunk_data["args"] = sanitize_args(chunk_data["args"])
        chunks.append(chunk_data)
    
    return chunks


def create_event_stream_message(
    message_chunk: Any,
    message_metadata: dict,
    thread_id: str,
    agent_name: str
) -> dict[str, Any]:
    """Create base event stream message.
    
    Ensures every message has a valid ID by generating one if missing.
    """
    content = message_chunk.content
    if not isinstance(content, str):
        content = json.dumps(safe_serialize(content), ensure_ascii=False)

    # Ensure message ID is always present
    message_id = getattr(message_chunk, 'id', None)
    if not message_id:
        message_id = f"run--{uuid4().hex}"
        logger.warning(
            f"[streaming] Generated ID {message_id} for {agent_name} message"
        )
        if hasattr(message_chunk, 'id'):
            try:
                message_chunk.id = message_id
            except AttributeError:
                pass

    event_message = {
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

    # Add reasoning content if available
    if message_chunk.additional_kwargs.get("reasoning_content"):
        event_message["reasoning_content"] = (
            message_chunk.additional_kwargs["reasoning_content"]
        )
    
    # Add react_thoughts from response_metadata (preferred) or additional_kwargs
    react_thoughts = None
    if hasattr(message_chunk, 'response_metadata') and message_chunk.response_metadata:
        react_thoughts = message_chunk.response_metadata.get("react_thoughts")
    if not react_thoughts and hasattr(message_chunk, 'additional_kwargs'):
        react_thoughts = message_chunk.additional_kwargs.get("react_thoughts")
    
    if react_thoughts:
        event_message["react_thoughts"] = react_thoughts

    # Include finish_reason
    finish_reason = None
    if hasattr(message_chunk, 'response_metadata') and message_chunk.response_metadata:
        finish_reason = message_chunk.response_metadata.get("finish_reason")
    if not finish_reason:
        finish_reason = message_metadata.get("finish_reason")
    if finish_reason:
        event_message["finish_reason"] = finish_reason

    return event_message


def create_interrupt_event(thread_id: str, event_data: dict) -> str:
    """Create interrupt event."""
    return make_event(
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


def process_initial_messages(message: dict, thread_id: str) -> None:
    """Process initial messages and send formatted events."""
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


async def process_message_chunk(
    message_chunk: Any,
    message_metadata: dict,
    thread_id: str,
    agent: tuple
) -> AsyncIterator[str]:
    """Process a single message chunk and yield appropriate events."""
    agent_name = get_agent_name(agent, message_metadata, message_chunk)
    safe_thread_id = sanitize_thread_id(thread_id)
    
    event_message = create_event_stream_message(
        message_chunk, message_metadata, thread_id, agent_name
    )
    
    # Check cache for react_thoughts if not in message_chunk
    if agent_name in ["pm_agent", "react_agent"]:
        message_id = event_message.get("id")
        if message_id and "react_thoughts" not in event_message:
            cached = get_cached_thoughts(message_id)
            if cached:
                event_message["react_thoughts"] = cached
                if isinstance(message_chunk, AIMessageChunk):
                    if not message_chunk.additional_kwargs:
                        message_chunk.additional_kwargs = {}
                    message_chunk.additional_kwargs["react_thoughts"] = cached

    if isinstance(message_chunk, ToolMessage):
        # Tool Message - Return the result
        tool_call_id = message_chunk.tool_call_id
        event_message["tool_call_id"] = tool_call_id
        yield make_event("tool_call_result", event_message)
        
    elif isinstance(message_chunk, AIMessageChunk):
        # AI Message Chunk - Streaming response
        if message_chunk.tool_calls:
            # Complete tool calls
            event_message["tool_calls"] = message_chunk.tool_calls
            
            # Include react_thoughts in tool_calls event for immediate display
            if "react_thoughts" not in event_message:
                chunk_thoughts = None
                if hasattr(message_chunk, 'response_metadata') and message_chunk.response_metadata:
                    chunk_thoughts = message_chunk.response_metadata.get("react_thoughts")
                if not chunk_thoughts and hasattr(message_chunk, 'additional_kwargs'):
                    chunk_thoughts = message_chunk.additional_kwargs.get("react_thoughts")
                if chunk_thoughts:
                    event_message["react_thoughts"] = chunk_thoughts
            
            processed_chunks = process_tool_call_chunks(message_chunk.tool_call_chunks)
            event_message["tool_call_chunks"] = processed_chunks
            yield make_event("tool_calls", event_message)
            
        elif message_chunk.tool_call_chunks:
            # Streaming tool call chunks
            processed_chunks = process_tool_call_chunks(message_chunk.tool_call_chunks)
            event_message["tool_call_chunks"] = processed_chunks
            yield make_event("tool_calls", event_message)
        else:
            # Regular content chunk
            yield make_event("message_chunk", event_message)
            
    elif isinstance(message_chunk, AIMessage):
        # Full AI Message (not streaming)
        if message_chunk.tool_calls:
            event_message["tool_calls"] = message_chunk.tool_calls
            yield make_event("tool_calls", event_message)
        else:
            yield make_event("message_chunk", event_message)
    else:
        # Unknown message type
        logger.warning(f"[{safe_thread_id}] Unknown message type: {type(message_chunk)}")
        yield make_event("message_chunk", event_message)


def extract_plan_data(current_plan: Any) -> dict:
    """Extract plan data from various plan formats."""
    plan_data = {}
    plan_obj = None
    
    if isinstance(current_plan, str):
        try:
            plan_obj = json.loads(current_plan)
        except (json.JSONDecodeError, TypeError):
            return plan_data
    elif isinstance(current_plan, dict):
        plan_obj = current_plan
    else:
        plan_obj = current_plan
    
    if isinstance(plan_obj, dict):
        plan_data["title"] = plan_obj.get("title", "")
        steps = plan_obj.get("steps", [])
        plan_data["steps"] = [
            {
                "title": step.get("title", "") if isinstance(step, dict) else getattr(step, "title", ""),
                "description": step.get("description", "") if isinstance(step, dict) else getattr(step, "description", ""),
                "step_type": _get_step_type(step),
                "execution_res": step.get("execution_res") if isinstance(step, dict) else getattr(step, "execution_res", None),
            }
            for step in steps
        ] if steps else []
    elif hasattr(plan_obj, 'title'):
        plan_data["title"] = plan_obj.title if not callable(plan_obj.title) else ""
        if hasattr(plan_obj, 'steps'):
            steps = plan_obj.steps if not callable(plan_obj.steps) else []
            plan_data["steps"] = [
                {
                    "title": step.title if hasattr(step, 'title') and not callable(step.title) else "",
                    "description": step.description if hasattr(step, 'description') and not callable(step.description) else "",
                    "step_type": _get_step_type(step),
                    "execution_res": getattr(step, "execution_res", None),
                }
                for step in steps
            ]
    
    return plan_data


def _get_step_type(step: Any) -> Optional[str]:
    """Extract step type from step object."""
    if isinstance(step, dict):
        step_type = step.get("step_type")
        if isinstance(step_type, dict):
            return step_type.get("value")
        return step_type
    elif hasattr(step, "step_type"):
        step_type = step.step_type
        if hasattr(step_type, "value"):
            return step_type.value
        return str(step_type) if step_type else None
    return None





