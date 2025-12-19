# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Thought Extractor Module

Provides consistent handling of agent thoughts for the Cursor-style
thought display feature. Ensures thoughts are always stored in
response_metadata (primary) and additional_kwargs (backup).
"""

import logging
import re
from typing import Any, List, Optional

from langchain_core.messages import AIMessage, BaseMessage

logger = logging.getLogger(__name__)


def extract_thoughts_from_response(
    content: str,
    tool_calls: Optional[List[dict]] = None
) -> List[dict]:
    """
    Extract thoughts from agent response content.
    
    Looks for thought patterns in the content and creates thought objects
    for each tool call or general reasoning.
    
    Args:
        content: The agent's response content
        tool_calls: Optional list of tool calls to associate thoughts with
        
    Returns:
        List of thought dicts with keys: thought, before_tool, step_index
    """
    thoughts = []
    
    if not content:
        return thoughts
    
    # Pattern 1: Explicit "Thought:" prefix
    thought_pattern = r'(?:Thought|Thinking|Reasoning):\s*(.+?)(?:\n|$)'
    matches = re.findall(thought_pattern, content, re.IGNORECASE)
    
    for i, match in enumerate(matches):
        thought_text = match.strip()
        if thought_text:
            thoughts.append({
                "thought": thought_text,
                "before_tool": bool(tool_calls and i < len(tool_calls)),
                "step_index": i
            })
    
    # Pattern 2: If no explicit thoughts found but has tool calls,
    # use the content as a thought if it looks like reasoning
    if not thoughts and tool_calls and content:
        # Check if content contains reasoning indicators
        reasoning_indicators = [
            "i need to", "i will", "let me", "first,", "next,",
            "to answer", "to find", "to get", "based on"
        ]
        content_lower = content.lower()
        if any(indicator in content_lower for indicator in reasoning_indicators):
            # Split by sentences and take first meaningful one
            sentences = content.split('.')
            if sentences:
                thought_text = sentences[0].strip()
                if len(thought_text) > 10:  # Minimum length filter
                    thoughts.append({
                        "thought": thought_text,
                        "before_tool": True,
                        "step_index": 0
                    })
    
    return thoughts


def attach_thoughts_to_message(
    message: BaseMessage,
    thoughts: List[dict],
    agent_name: str = "unknown"
) -> BaseMessage:
    """
    Attach thoughts to a message consistently.
    
    Always stores thoughts in both response_metadata (primary, more reliable)
    and additional_kwargs (backup for compatibility).
    
    Args:
        message: The message to attach thoughts to
        thoughts: List of thought dicts
        agent_name: Name of the agent for logging
        
    Returns:
        The message with thoughts attached
    """
    if not thoughts:
        return message
    
    # Ensure additional_kwargs exists
    if not hasattr(message, 'additional_kwargs') or not message.additional_kwargs:
        message.additional_kwargs = {}
    
    # Ensure response_metadata exists
    if not hasattr(message, 'response_metadata') or not message.response_metadata:
        message.response_metadata = {}
    
    # Store in both places for maximum compatibility
    message.additional_kwargs["react_thoughts"] = thoughts
    message.response_metadata["react_thoughts"] = thoughts
    
    logger.info(
        f"[{agent_name}] Attached {len(thoughts)} thoughts to message "
        f"(both additional_kwargs and response_metadata)"
    )
    
    return message


def merge_thoughts(existing: List[dict], new: List[dict]) -> List[dict]:
    """
    Merge two lists of thoughts, avoiding duplicates.
    
    Args:
        existing: Existing thoughts list
        new: New thoughts to merge
        
    Returns:
        Merged list of thoughts
    """
    if not new:
        return existing or []
    if not existing:
        return new
    
    # Use thought text as key for deduplication
    existing_texts = {t.get("thought", "") for t in existing}
    result = list(existing)
    
    for thought in new:
        if thought.get("thought", "") not in existing_texts:
            # Update step_index for new thoughts
            thought["step_index"] = len(result)
            result.append(thought)
            existing_texts.add(thought.get("thought", ""))
    
    return result


def get_thoughts_from_message(message: BaseMessage) -> List[dict]:
    """
    Get thoughts from a message, checking both metadata locations.
    
    Args:
        message: The message to get thoughts from
        
    Returns:
        List of thoughts or empty list
    """
    # Check response_metadata first (primary location)
    if hasattr(message, 'response_metadata') and message.response_metadata:
        thoughts = message.response_metadata.get("react_thoughts")
        if thoughts:
            return thoughts
    
    # Fall back to additional_kwargs
    if hasattr(message, 'additional_kwargs') and message.additional_kwargs:
        thoughts = message.additional_kwargs.get("react_thoughts")
        if thoughts:
            return thoughts
    
    return []


def create_thought(
    text: str,
    before_tool: bool = True,
    step_index: int = 0
) -> dict:
    """
    Create a thought dictionary.
    
    Args:
        text: The thought text
        before_tool: Whether this thought comes before a tool call
        step_index: Index of this thought in the sequence
        
    Returns:
        Thought dictionary
    """
    return {
        "thought": text,
        "before_tool": before_tool,
        "step_index": step_index
    }


def extract_plan_step_thoughts(
    plan_steps: List[dict],
    prefix: str = ""
) -> List[dict]:
    """
    Extract thoughts from plan steps.
    
    Converts plan step descriptions into thought format for display.
    
    Args:
        plan_steps: List of plan step dictionaries
        prefix: Optional prefix for thought text
        
    Returns:
        List of thoughts
    """
    thoughts = []
    
    for i, step in enumerate(plan_steps):
        description = ""
        if isinstance(step, dict):
            description = step.get("description", "") or step.get("title", "")
        elif hasattr(step, "description"):
            description = step.description or getattr(step, "title", "")
        
        if description:
            thought_text = f"{prefix}{description}" if prefix else description
            thoughts.append({
                "thought": thought_text,
                "before_tool": True,
                "step_index": i
            })
    
    return thoughts

