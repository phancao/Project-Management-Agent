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


def _create_task_summary(tasks: list, max_items: int) -> list:
    """
    Create an intelligent summary of tasks by grouping and aggregating data.
    
    Args:
        tasks: List of task dictionaries
        max_items: Maximum number of sample tasks to include
        
    Returns:
        List containing summary statistics and representative samples
    """
    if not tasks:
        return []
    
    # Analyze all tasks to create comprehensive summary
    status_counts = {}
    priority_counts = {}
    assignee_counts = {}
    total_hours = 0
    completed_hours = 0
    high_priority_tasks = []
    recent_tasks = []
    
    for task in tasks:
        if isinstance(task, dict):
            # Count by status
            status = task.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count by priority
            priority = task.get("priority", "unknown")
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            # Count by assignee
            assignee = task.get("assigned_to") or task.get("assignee") or "unassigned"
            assignee_counts[assignee] = assignee_counts.get(assignee, 0) + 1
            
            # Sum hours
            hours = task.get("estimated_hours", 0) or 0
            total_hours += hours
            if status in ["done", "completed", "closed"]:
                completed_hours += hours
            
            # Collect high priority tasks
            if priority in ["high", "critical", "urgent"]:
                high_priority_tasks.append(task)
            
            # Collect recent tasks (by updated_at or created_at)
            if task.get("updated_at") or task.get("created_at"):
                recent_tasks.append(task)
    
    # Sort recent tasks by date (most recent first)
    recent_tasks.sort(
        key=lambda t: t.get("updated_at") or t.get("created_at") or "",
        reverse=True
    )
    
    # Create summary structure
    summary_items = []
    
    # Overall statistics
    summary_items.append({
        "_summary_type": "statistics",
        "total_tasks": len(tasks),
        "status_breakdown": status_counts,
        "priority_breakdown": priority_counts,
        "assignee_breakdown": assignee_counts,
        "total_estimated_hours": round(total_hours, 1),
        "completed_hours": round(completed_hours, 1),
        "completion_percentage": round((completed_hours / total_hours * 100) if total_hours > 0 else 0, 1)
    })
    
    # Representative samples: high priority tasks first, then recent tasks
    samples = []
    sample_count = min(max_items, len(tasks))
    
    # Add high priority tasks as samples (up to half of max_items)
    high_priority_samples = min(len(high_priority_tasks), sample_count // 2)
    samples.extend(high_priority_tasks[:high_priority_samples])
    
    # Add recent tasks as samples (fill remaining slots)
    remaining_slots = sample_count - len(samples)
    for task in recent_tasks:
        if len(samples) >= sample_count:
            break
        # Avoid duplicates
        if task not in samples:
            samples.append(task)
    
    # If we still need more samples, add from the beginning
    if len(samples) < sample_count:
        for task in tasks:
            if len(samples) >= sample_count:
                break
            if task not in samples:
                samples.append(task)
    
    # Add samples with metadata
    if samples:
        summary_items.append({
            "_summary_type": "samples",
            "_note": f"Showing {len(samples)} representative tasks (high priority and recent)",
            "_samples": samples
        })
    
    return summary_items


def _compress_large_array(data: Any, max_items: int = 20) -> Any:
    """
    Compress large arrays by creating intelligent summaries instead of cutting off content.
    
    This function analyzes the data structure and creates meaningful summaries:
    - For task lists: Groups by status, priority, assignee and shows statistics + samples
    - For general arrays: Analyzes structure and creates category summaries
    
    Args:
        data: Data structure (dict, list, etc.)
        max_items: Maximum items to keep in arrays (default 20 for token efficiency)
        
    Returns:
        Compressed data structure with summaries instead of cut-off content
    """
    if isinstance(data, list):
        if len(data) > max_items:
            # Check if this looks like a task list
            is_task_list = (
                len(data) > 0 and
                isinstance(data[0], dict) and
                any(key in data[0] for key in ["status", "priority", "assigned_to", "assignee", "task_id", "title"])
            )
            
            if is_task_list:
                # Use intelligent task summarization
                summary = _create_task_summary(data, max_items)
                logger.info(f"Compressed task list from {len(data)} items to summary with {len(summary)} sections")
                return summary
            else:
                # For generic arrays, create category-based summary
                # Group items by type or key characteristics
                item_types = {}
                for item in data:
                    item_type = type(item).__name__
                    if item_type not in item_types:
                        item_types[item_type] = []
                    item_types[item_type].append(item)
                
                # Create summary with type breakdown and samples
                summary = [{
                    "_summary_type": "array_summary",
                    "total_items": len(data),
                    "type_breakdown": {k: len(v) for k, v in item_types.items()},
                    "_note": f"Array contains {len(data)} items across {len(item_types)} types"
                }]
                
                # Add samples from each type (proportional to type frequency)
                samples = []
                samples_per_type = max(1, max_items // len(item_types)) if item_types else max_items
                for item_type, items in item_types.items():
                    samples.extend(items[:samples_per_type])
                    if len(samples) >= max_items:
                        break
                
                if samples:
                    summary.append({
                        "_summary_type": "samples",
                        "_note": f"Showing {len(samples)} representative items",
                        "_samples": samples[:max_items]
                    })
                
                logger.info(f"Compressed array from {len(data)} to summary with {len(summary)} sections")
                return summary
        else:
            return [_compress_large_array(item, max_items) for item in data]
    elif isinstance(data, dict):
        # Check if this is a task list response - use intelligent summarization
        if "tasks" in data and isinstance(data["tasks"], list) and len(data["tasks"]) > max_items:
            tasks = data["tasks"]
            # Always use intelligent summarization for task lists
            compressed_tasks = _create_task_summary(tasks, max_items)
            logger.info(f"Compressed task list from {len(tasks)} to summary (intelligent summarization)")
            return {**data, "tasks": compressed_tasks, "_total_tasks": len(tasks), "_compressed": True, "_compression_method": "intelligent_summary"}
        else:
            return {k: _compress_large_array(v, max_items) for k, v in data.items()}
    else:
        return data


def sanitize_tool_response(content: str, max_length: int = 40000, compress_arrays: bool = True) -> str:
    """
    Sanitize tool response to remove extra tokens and invalid content.
    
    This function:
    - Strips whitespace and trailing tokens
    - Compresses large arrays (like task lists) to prevent token overflow
    - Truncates excessively long responses (default 40k chars ≈ 10k tokens)
    - Cleans up common garbage patterns
    - Attempts JSON repair for JSON-like responses
    
    Args:
        content: Tool response content
        max_length: Maximum allowed length (default 40000 chars ≈ 10k tokens for English)
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
            # Use more aggressive compression (20 items instead of 50)
            compressed = _compress_large_array(parsed, max_items=20)
            content = json.dumps(compressed, ensure_ascii=False)
            logger.info(f"Compressed tool response JSON structure")
        except (json.JSONDecodeError, TypeError):
            # Not valid JSON, skip compression
            pass
    
    # Truncate if too long to prevent token overflow
    # 40k chars ≈ 10k tokens (assuming 4 chars/token for English)
    # This leaves room for other content in the full message context
    if len(content) > max_length:
        logger.warning(f"Tool response truncated from {len(content)} to {max_length} chars (≈{max_length//4} tokens)")
        content = content[:max_length].rstrip() + f"... [truncated from {len(content)} chars]"
    
    # Remove common garbage patterns that appear from some models
    # These are often seen from quantized models with output corruption
    garbage_patterns = [
        r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]',  # Control characters
    ]
    
    for pattern in garbage_patterns:
        content = re.sub(pattern, '', content)
    
    return content
