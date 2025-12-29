# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import asyncio
import logging
from contextvars import ContextVar
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ContextVar to store the current thread_id for the execution context
# This allows deep functions (like tool interceptors) to know which thread they are running in
current_thread_id: ContextVar[Optional[str]] = ContextVar("current_thread_id", default=None)

# Global registry of async queues for streaming tool results
# Key: thread_id, Value: asyncio.Queue
_tool_result_queues: Dict[str, asyncio.Queue] = {}

def get_tool_result_queue(thread_id: str) -> asyncio.Queue:
    """Get or create async queue for thread."""
    if thread_id not in _tool_result_queues:
        _tool_result_queues[thread_id] = asyncio.Queue()
    return _tool_result_queues[thread_id]

def cleanup_tool_result_queue(thread_id: str):
    """Cleanup queue after streaming completes."""
    if thread_id in _tool_result_queues:
        del _tool_result_queues[thread_id]

def register_tool_result(tool_name: str, result: str, tool_call_id: Optional[str] = None):
    """
    Register a tool result to be streamed immediately via side-channel.
    Uses context var to determine current thread_id.
    """
    thread_id = current_thread_id.get()
    if not thread_id:
        # This is normal for non-streaming contexts or background tasks
        return

    if thread_id in _tool_result_queues:
        queue = _tool_result_queues[thread_id]
        
        item = {
            "tool_name": tool_name,
            "result": result,
            "tool_call_id": tool_call_id
        }
        
        try:
            queue.put_nowait(item)
        except Exception as e:
            logger.error(f"Failed to push tool result for {tool_name}: {e}")
