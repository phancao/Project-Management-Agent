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
        pass

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


def _compress_project_list(projects: list) -> list:
    """
    Intelligently compress a list of projects by preserving searchable fields (id, name) for ALL projects,
    while compressing other fields (description, etc.) to save tokens.
    
    This allows the agent to search through all projects even when the list is large.
    The key insight: agents need to search by project name/ID, so we MUST preserve these for all projects.
    
    Args:
        projects: List of project dictionaries
        
    Returns:
        Compressed list with all project ids/names preserved, but other fields compressed
    """
    if not projects:
        return projects
    
    # Preserve essential searchable fields for ALL projects
    compressed = []
    essential_fields = ["id", "name", "key"]  # Fields needed for searching/identifying projects
    optional_fields = ["status", "description"]  # Can be truncated/compressed
    
    for project in projects:
        if isinstance(project, dict):
            compressed_project = {}
            # Always preserve essential fields (needed for searching)
            for field in essential_fields:
                if field in project:
                    compressed_project[field] = project[field]
            # Compress optional fields to save tokens
            for field in optional_fields:
                if field in project:
                    value = project[field]
                    if isinstance(value, str) and len(value) > 30:
                        compressed_project[field] = value[:30] + "..."
                    else:
                        compressed_project[field] = value
            # Preserve other small fields
            for key, value in project.items():
                if key not in essential_fields and key not in optional_fields:
                    if isinstance(value, (str, int, float, bool, type(None))):
                        # Only keep small values
                        if isinstance(value, str) and len(value) <= 50:
                            compressed_project[key] = value
                        elif not isinstance(value, str):
                            compressed_project[key] = value
            compressed.append(compressed_project)
        else:
            compressed.append(project)
    
    logger.info(f"Compressed project list: preserved id/name for all {len(compressed)} projects (essential for searching)")
    return compressed


def _compress_sprint_list(sprints: list) -> list:
    """
    Intelligently compress a list of sprints by preserving searchable fields (id, name, status) for ALL sprints,
    while compressing other fields (goal, dates, etc.) to save tokens.
    
    This allows the agent to search through all sprints even when the list is large.
    The key insight: agents need to search by sprint name/number/ID, so we MUST preserve these for all sprints.
    
    CRITICAL: Sprint names often contain numbers (e.g., "Sprint 4", "Sprint 10"), so preserving ALL sprint
    names is essential for the agent to find specific sprints by number.
    
    Args:
        sprints: List of sprint dictionaries
        
    Returns:
        Compressed list with all sprint ids/names/status preserved, but other fields compressed
    """
    if not sprints:
        return sprints
    
    # Preserve essential searchable fields for ALL sprints
    compressed = []
    essential_fields = ["id", "name", "status"]  # Fields needed for searching/identifying sprints
    optional_fields = ["project_id", "start_date", "end_date"]  # Can be truncated/compressed
    drop_fields = ["goal", "capacity_hours", "planned_hours", "created_at", "updated_at"]  # Drop large/unnecessary fields
    
    for sprint in sprints:
        if isinstance(sprint, dict):
            compressed_sprint = {}
            # Always preserve essential fields (needed for searching)
            for field in essential_fields:
                if field in sprint:
                    compressed_sprint[field] = sprint[field]
            # Compress optional fields to save tokens
            for field in optional_fields:
                if field in sprint:
                    value = sprint[field]
                    if isinstance(value, str) and len(value) > 30:
                        compressed_sprint[field] = value[:30] + "..."
                    else:
                        compressed_sprint[field] = value
            # Preserve other small fields (but drop large ones)
            for key, value in sprint.items():
                if key not in essential_fields and key not in optional_fields and key not in drop_fields:
                    if isinstance(value, (str, int, float, bool, type(None))):
                        # Only keep small values
                        if isinstance(value, str) and len(value) <= 50:
                            compressed_sprint[key] = value
                        elif not isinstance(value, str):
                            compressed_sprint[key] = value
            compressed.append(compressed_sprint)
        else:
            compressed.append(sprint)
    
    logger.info(f"Compressed sprint list: preserved id/name/status for all {len(compressed)} sprints (essential for searching)")
    return compressed

def _compress_task_list(tasks: list) -> list:
    """
    Intelligently compress a list of tasks by preserving essential fields (id, title, status, assignee) for ALL tasks,
    while dropping description and other heavy fields.
    
    This ensures the agent receives the FULL LIST of tasks (as requested by users) rather than a statistical summary.
    
    Args:
        tasks: List of task dictionaries
        
    Returns:
        Compressed list with essential fields preserved for all tasks
    """
    if not tasks:
        return tasks
    
    compressed = []
    # Essential fields to keep for EVERY task (keep it minimal to fit 100+ tasks)
    essential_fields = ["id", "task_id", "title", "name", "status"]
    # Optional but useful small fields
    useful_fields = ["priority", "assigned_to", "assignee", "due_date", "end_date"]
    
    for task in tasks:
        if isinstance(task, dict):
            compressed_task = {}
            
            # Map common variations
            # (e.g. handle task_id vs id, title vs name)
            
            # 1. ID
            if "id" in task: compressed_task["id"] = task["id"]
            elif "task_id" in task: compressed_task["id"] = task["task_id"]
            
            # 2. Title
            if "title" in task: compressed_task["title"] = task["title"]
            elif "name" in task: compressed_task["title"] = task["name"]
            
            # 3. Status
            if "status" in task: compressed_task["status"] = task["status"]
            
            # 4. Assignee
            if "assigned_to" in task: compressed_task["assignee"] = task["assigned_to"]
            elif "assignee" in task: compressed_task["assignee"] = task["assignee"]
            
            # 5. Priority
            if "priority" in task: compressed_task["priority"] = task["priority"]
            
            # 6. Date
            if "due_date" in task: compressed_task["due_date"] = task["due_date"]
            elif "end_date" in task: compressed_task["due_date"] = task["end_date"]
            
            compressed.append(compressed_task)
        else:
            compressed.append(task)
            
    logger.info(f"Compressed task list: preserved essential fields for all {len(compressed)} tasks")
    return compressed


def _compress_large_array(data: Any, max_items: int = 20) -> Any:
    """
    Compress large arrays by creating intelligent summaries instead of cutting off content.
    
    This function analyzes the data structure and creates meaningful summaries:
    - For project lists: Preserves ALL project IDs and names (searchable fields) while compressing other fields
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
            # Check if this looks like a sprint list (has id, name, status, project_id, start_date, end_date)
            # CRITICAL: Sprint lists have "status" field, which distinguishes them from project lists
            is_sprint_list = (
                len(data) > 0 and
                isinstance(data[0], dict) and
                "id" in data[0] and
                "name" in data[0] and
                "status" in data[0] and
                ("project_id" in data[0] or "start_date" in data[0] or "end_date" in data[0]) and
                not any(key in data[0] for key in ["priority", "assigned_to", "assignee", "task_id", "title", "description"])
            )
            
            if is_sprint_list:
                # Use intelligent sprint compression (preserves all ids/names/status)
                compressed = _compress_sprint_list(data)
                logger.info(f"Compressed sprint list from {len(data)} to {len(compressed)} items (preserved all ids/names/status)")
                return compressed
            
            # Check if this looks like a project list (has id and name fields, but NOT status)
            is_project_list = (
                len(data) > 0 and
                isinstance(data[0], dict) and
                "id" in data[0] and
                "name" in data[0] and
                not any(key in data[0] for key in ["status", "priority", "assigned_to", "assignee", "task_id", "title"])
            )
            
            if is_project_list:
                # Use intelligent project compression (preserves all ids/names)
                compressed = _compress_project_list(data)
                logger.info(f"Compressed project list from {len(data)} to {len(compressed)} items (preserved all ids/names)")
                return compressed
            
            # Check if this looks like a task list
            is_task_list = (
                len(data) > 0 and
                isinstance(data[0], dict) and
                any(key in data[0] for key in ["status", "priority", "assigned_to", "assignee", "task_id", "title"])
            )
            
            if is_task_list:
                # CRITICAL CHANGE: Use intelligent task compression (list all) instead of summarization
                # Users want to see the full list, not just stats
                compressed = _compress_task_list(data)
                logger.info(f"Compressed task list from {len(data)} items to {len(compressed)} items (preserved essential fields)")
                return compressed
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
        # Check if this is a sprint list response - use intelligent sprint compression
        if "sprints" in data and isinstance(data["sprints"], list) and len(data["sprints"]) > 0:
            sprints = data["sprints"]
            if len(sprints) > 0 and isinstance(sprints[0], dict) and "id" in sprints[0] and "name" in sprints[0] and "status" in sprints[0]:
                # This is a sprint list - preserve all ids/names/status
                compressed_sprints = _compress_sprint_list(sprints)
                logger.info(f"Compressed sprints list from {len(sprints)} to {len(compressed_sprints)} items (preserved all ids/names/status)")
                
                # DEBUG: Print compressed sprint data to see what agent receives
                try:
                    sprint_names = [s.get("name", "N/A") for s in compressed_sprints if isinstance(s, dict)]
                    sprint_ids = [s.get("id", "N/A") for s in compressed_sprints if isinstance(s, dict)]
                    
                    # Check if "Sprint 4" or "4" is in any sprint name
                    sprint_4_found = any("4" in str(s.get("name", "")).lower() or "sprint 4" in str(s.get("name", "")).lower() for s in compressed_sprints if isinstance(s, dict))
                except Exception as e:
                    pass
                
                # Add helpful note for agents on how to search for sprints
                result = {
                    **data, 
                    "sprints": compressed_sprints, 
                    "_compressed": True, 
                    "_compression_method": "sprint_list_preserve_ids",
                    "_note": "✅ ALL sprint IDs and names are preserved. To find a specific sprint (e.g., 'Sprint 4'): 1) Search through the 'sprints' array, 2) Look for a sprint where the 'name' field contains the number (e.g., '4' or 'Sprint 4'), 3) Extract the 'id' field from that sprint, 4) Use that 'id' in subsequent tool calls."
                }
                
                # DEBUG: Print the final JSON structure
                try:
                    result_json = json.dumps(result, indent=2, default=str)
                    
                    # Also log a sample sprint structure for debugging
                    if compressed_sprints and len(compressed_sprints) > 0:
                        sample_sprint = compressed_sprints[0] if isinstance(compressed_sprints[0], dict) else {}
                except Exception as e:
                    pass
                
                return result
        
        # Check if this is a project list response - use intelligent project compression
        if "projects" in data and isinstance(data["projects"], list) and len(data["projects"]) > 0:
            projects = data["projects"]
            if len(projects) > 0 and isinstance(projects[0], dict) and "id" in projects[0] and "name" in projects[0]:
                # This is a project list - preserve all ids/names
                compressed_projects = _compress_project_list(projects)
                logger.info(f"Compressed projects list from {len(projects)} to {len(compressed_projects)} items (preserved all ids/names)")
                return {**data, "projects": compressed_projects, "_compressed": True, "_compression_method": "project_list_preserve_ids"}
        
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


def _truncate_json_safely(content: str, max_length: int) -> str:
    """
    Safely truncate JSON content by adding a note field instead of breaking the JSON structure.
    
    Args:
        content: JSON string to truncate
        max_length: Maximum allowed length
        
    Returns:
        Truncated JSON string with note field, or original if not JSON
    """
    if not (content.startswith('{') or content.startswith('[')):
        return content[:max_length]
    
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            # Add note as a field in the JSON object
            note_text = "Result was truncated to fit token limits. This is a COMPLETE result - do NOT retry this tool call."
            parsed["_truncation_note"] = note_text
            result = json.dumps(parsed, ensure_ascii=False)
            if len(result) <= max_length:
                return result
            # If adding note makes it too long, remove it and truncate the original
            # But try to keep JSON valid by truncating at a boundary
        # If it's a list or we can't add a field, fall through to simple truncation
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Fallback: simple truncation (will break JSON, but we'll add note after)
    return content[:max_length]


def sanitize_tool_response(content: str, max_length: int = 40000, compress_arrays: bool = True) -> str:
    """
    Sanitize tool response to remove extra tokens and invalid content.
    
    NOTE: Compression is DISABLED because the system has auto context compression
    that kicks in at ~90% context usage. This function now only does basic cleanup.
    
    This function:
    - Strips whitespace and trailing tokens
    - Extracts valid JSON from content with trailing garbage
    - Cleans up common garbage patterns (control characters)
    
    Args:
        content: Tool response content
        max_length: IGNORED - no truncation applied (auto context compression handles this)
        compress_arrays: IGNORED - no compression applied (auto context compression handles this)
        
    Returns:
        Cleaned content string (no compression/truncation)
    """
    if not content:
        return content
    
    content = content.strip()
    
    # Only extract valid JSON to remove trailing garbage tokens
    if content.startswith('{') or content.startswith('['):
        content = _extract_json_from_content(content)
    
    # Remove common garbage patterns that appear from some models
    # These are often seen from quantized models with output corruption
    garbage_patterns = [
        r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]',  # Control characters
    ]
    
    for pattern in garbage_patterns:
        content = re.sub(pattern, '', content)
    
    return content

