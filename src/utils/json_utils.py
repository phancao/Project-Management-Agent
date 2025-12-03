# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import logging
import re
from typing import Any

import json_repair

logger = logging.getLogger(__name__)


def sanitize_args(args: Any) -> str:
    """
    Sanitize tool call arguments to prevent special character issues.

    Args:
        args: Tool call arguments string

    Returns:
        str: Sanitized arguments string
    """
    if not isinstance(args, str):
        return ""
    else:
        return (
            args.replace("[", "&#91;")
            .replace("]", "&#93;")
            .replace("{", "&#123;")
            .replace("}", "&#125;")
        )


def _extract_json_from_content(content: str) -> str:
    """
    Extract valid JSON from content that may have extra tokens.
    
    Attempts to find the last valid JSON closing bracket and truncate there.
    Handles both objects {} and arrays [].
    
    Args:
        content: String that may contain JSON with extra tokens
        
    Returns:
        String with potential JSON extracted or original content
    """
    content = content.strip()
    
    # Try to find a complete JSON object or array
    # Look for the last closing brace/bracket that could be valid JSON
    
    # Track counters and whether we've seen opening brackets
    brace_count = 0
    bracket_count = 0
    seen_opening_brace = False
    seen_opening_bracket = False
    in_string = False
    escape_next = False
    last_valid_end = -1
    
    for i, char in enumerate(content):
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if in_string:
            continue
        
        if char == '{':
            brace_count += 1
            seen_opening_brace = True
        elif char == '}':
            brace_count -= 1
            # Only mark as valid end if we started with opening brace and reached balanced state
            if brace_count == 0 and seen_opening_brace:
                last_valid_end = i
        elif char == '[':
            bracket_count += 1
            seen_opening_bracket = True
        elif char == ']':
            bracket_count -= 1
            # Only mark as valid end if we started with opening bracket and reached balanced state
            if bracket_count == 0 and seen_opening_bracket:
                last_valid_end = i
    
    if last_valid_end > 0:
        truncated = content[:last_valid_end + 1]
        if truncated != content:
            logger.debug(f"Truncated content from {len(content)} to {len(truncated)} chars")
        return truncated
    
    return content


def repair_json_output(content: str) -> str:
    """
    Repair and normalize JSON output.

    Handles:
    - JSON with extra tokens after closing brackets
    - Incomplete JSON structures
    - Malformed JSON from quantized models
    
    Args:
        content (str): String content that may contain JSON

    Returns:
        str: Repaired JSON string, or original content if not JSON
    """
    content = content.strip()
    
    if not content:
        return content

    # First attempt: try to extract valid JSON if there are extra tokens
    content = _extract_json_from_content(content)

    try:
        # Try to repair and parse JSON
        repaired_content = json_repair.loads(content)
        if not isinstance(repaired_content, dict) and not isinstance(
            repaired_content, list
        ):
            logger.warning("Repaired content is not a valid JSON object or array.")
            return content
        content = json.dumps(repaired_content, ensure_ascii=False)
    except Exception as e:
        logger.debug(f"JSON repair failed: {e}")

    return content


def _compress_large_array(data: Any, max_items: int = 50) -> Any:
    """
    Compress large arrays by keeping only a summary and sample items.
    
    Args:
        data: Data structure (dict, list, etc.)
        max_items: Maximum items to keep in arrays
        
    Returns:
        Compressed data structure
    """
    if isinstance(data, list):
        if len(data) > max_items:
            # Keep first few and last few items, add summary
            keep_count = max_items // 2
            compressed = (
                data[:keep_count] + 
                [{"_summary": f"... {len(data) - max_items} more items ..."}] +
                data[-keep_count:]
            )
            logger.info(f"Compressed array from {len(data)} to {len(compressed)} items")
            return compressed
        else:
            return [_compress_large_array(item, max_items) for item in data]
    elif isinstance(data, dict):
        # Check if this is a task list response
        if "tasks" in data and isinstance(data["tasks"], list) and len(data["tasks"]) > max_items:
            tasks = data["tasks"]
            keep_count = max_items // 2
            compressed_tasks = (
                tasks[:keep_count] +
                [{"_summary": f"... {len(tasks) - max_items} more tasks (total: {len(tasks)}) ..."}] +
                tasks[-keep_count:]
            )
            logger.info(f"Compressed task list from {len(tasks)} to {len(compressed_tasks)} tasks")
            return {**data, "tasks": compressed_tasks, "_total_tasks": len(tasks)}
        else:
            return {k: _compress_large_array(v, max_items) for k, v in data.items()}
    else:
        return data


def sanitize_tool_response(content: str, max_length: int = 50000, compress_arrays: bool = True) -> str:
    """
    Sanitize tool response to remove extra tokens and invalid content.
    
    This function:
    - Strips whitespace and trailing tokens
    - Compresses large arrays (like task lists) to prevent token overflow
    - Truncates excessively long responses
    - Cleans up common garbage patterns
    - Attempts JSON repair for JSON-like responses
    
    Args:
        content: Tool response content
        max_length: Maximum allowed length (default 50000 chars)
        compress_arrays: Whether to compress large arrays (default True)
        
    Returns:
        Sanitized content string
    """
    if not content:
        return content
    
    content = content.strip()
    
    # First, try to extract valid JSON to remove trailing tokens
    if content.startswith('{') or content.startswith('['):
        content = _extract_json_from_content(content)
    
    # Try to compress large arrays if it's JSON
    if compress_arrays and (content.startswith('{') or content.startswith('[')):
        try:
            parsed = json.loads(content)
            compressed = _compress_large_array(parsed, max_items=50)
            content = json.dumps(compressed, ensure_ascii=False)
            logger.info(f"Compressed tool response JSON structure")
        except (json.JSONDecodeError, TypeError):
            # Not valid JSON, skip compression
            pass
    
    # Truncate if too long to prevent token overflow
    if len(content) > max_length:
        logger.warning(f"Tool response truncated from {len(content)} to {max_length} chars")
        content = content[:max_length].rstrip() + "..."
    
    # Remove common garbage patterns that appear from some models
    # These are often seen from quantized models with output corruption
    garbage_patterns = [
        r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]',  # Control characters
    ]
    
    for pattern in garbage_patterns:
        content = re.sub(pattern, '', content)
    
    return content
