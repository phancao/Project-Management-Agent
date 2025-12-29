# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
PM Tools for Agent Chat

Tools that wrap PMHandler methods to allow agents to query and manage
project management data (projects, tasks, sprints, epics, etc.).
"""
import json
import logging
import asyncio
import datetime
from typing import Annotated, Optional, List, Dict, Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Helper to get timestamp
def get_ts():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


# Global PM handler instance - will be set by conversation flow manager
_pm_handler = None

# Global current project - will be set by pm_chat_stream endpoint
_current_project_id = None


def set_pm_handler(handler):
    """Set the PM handler instance for tools to use"""
    global _pm_handler
    _pm_handler = handler
    logger.info(f"PM handler set for tools: {handler.__class__.__name__}")


def set_current_project(project_id: str):
    """Set the current project ID selected by the user in the UI"""
    global _current_project_id
    _current_project_id = project_id
    logger.info(f"Current project set: {project_id}")


def get_current_project_id() -> Optional[str]:
    """Get the current project ID selected by the user"""
    return _current_project_id


def _ensure_pm_handler():
    """Ensure PM handler is available"""
    if _pm_handler is None:
        raise RuntimeError(
            "PM handler not initialized. "
            "Please ensure PM provider is configured and conversation flow manager is initialized."
        )
    return _pm_handler


async def _call_handler_method(method, *args, **kwargs):
    """Helper to call async or sync handler methods"""
    result = method(*args, **kwargs)
    if asyncio.iscoroutine(result):
        return await result
    return result


@tool
async def get_current_project() -> str:
    """Get the currently selected project and provider from the UI.
    
    **IMPORTANT**: Call this tool FIRST before any other PM tool if you need project context.
    This returns the project that the user has selected in the UI header.
    
    The project_id is in the format "provider_id:project_id" which includes:
    - provider_id: UUID of the PM provider connection (OpenProject, JIRA, etc.)
    - project_id: The actual project ID within that provider
    
    Returns:
        JSON string with current project info:
        - project_id: The full composite ID (provider_id:project_id) - USE THIS for all tool calls
        - provider_id: The PM provider UUID (extracted from project_id)
        - actual_project_id: The project ID within the provider (extracted from project_id)
        - project_name: The project name
        - provider_type: Type of provider (openproject, jira, etc.)
        - has_project: Whether a project is selected
        
    If no project is selected, you may need to ask the user to select one,
    or call list_projects to show available projects.
    """
    try:
        composite_project_id = get_current_project_id()
        
        if not composite_project_id:
            return json.dumps({
                "success": True,
                "has_project": False,
                "project_id": None,
                "provider_id": None,
                "actual_project_id": None,
                "project_name": None,
                "provider_type": None,
                "message": "No project is currently selected. Please ask the user to select a project from the header dropdown, or use list_projects to show available projects."
            }, indent=2)
        
        # Parse composite ID (format: provider_id:project_id)
        provider_id = None
        actual_project_id = composite_project_id
        
        if ":" in composite_project_id:
            parts = composite_project_id.split(":", 1)
            provider_id = parts[0]
            actual_project_id = parts[1]
        
        # Try to get project details
        project_name = "Unknown"
        provider_type = "unknown"
        try:
            handler = _ensure_pm_handler()
            project = await _call_handler_method(handler.get_project, composite_project_id)
            if isinstance(project, dict):
                project_name = project.get("name", "Unknown")
                provider_type = project.get("provider_type", "unknown")
        except Exception as e:
            logger.warning(f"[PM-TOOLS] get_current_project: Could not fetch project details: {e}")
        
        # Return structured JSON that the agent can easily parse
        result_json = {
            "success": True,
            "has_project": True,
            "project_id": composite_project_id,  # CRITICAL: Use this ID
            "name": project_name,
            "provider_id": provider_id,
            "provider_type": provider_type,
            "note": "Use the 'project_id' field value for any tool requiring a project_id."
        }
        
        return json.dumps(result_json, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting current project: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "has_project": False
        }, indent=2)


@tool
async def list_projects() -> str:
    """List all available projects from the PM provider.
    
    Returns:
        JSON string with list of projects, each containing:
        - id: Project ID
        - name: Project name
        - description: Project description
        - status: Project status
    """
    try:
        handler = _ensure_pm_handler()
        projects = await handler.list_all_projects()
        result = json.dumps({
            "success": True,
            "projects": projects,
            "count": len(projects)
        }, indent=2, default=str)
        
        # CRITICAL: Truncate large results to prevent token overflow in ReAct agent scratchpad
        # Max 1000 tokens = 4000 chars per tool result
        from backend.utils.json_utils import sanitize_tool_response
        max_chars = 4000  # 1000 tokens * 4 chars/token
        original_length = len(result)
        if original_length > max_chars:
            logger.warning(
                f"[PM-TOOLS] list_projects returned {original_length:,} chars "
                f"(≈{original_length//4:,} tokens). Compressing to {max_chars:,} chars."
            )
            # Parse JSON to add metadata about compression
            # This metadata will be preserved by sanitize_tool_response
            try:
                parsed = json.loads(result)
                if isinstance(parsed, dict):
                    parsed["_metadata"] = {
                        "_compressed": True,
                        "_original_count": parsed.get("count", len(parsed.get("projects", []))),
                        "_original_length": original_length,
                        "_note": "⚠️ CRITICAL: This result was intelligently compressed to fit token limits. This is a COMPLETE result - do NOT retry this tool call. Use the provided projects to proceed with your task."
                    }
                    result = json.dumps(parsed, indent=2, default=str)
            except (json.JSONDecodeError, TypeError):
                pass  # If not JSON, use sanitize_tool_response as fallback
            
            result = sanitize_tool_response(result, max_length=max_chars, compress_arrays=True)
            logger.info(f"[PM-TOOLS] ✅ list_projects compressed to {len(result):,} chars (≈{len(result)//4:,} tokens)")
        
        return result
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
async def get_current_project_details() -> str:
    """Get the description and details of the currently selected project from the UI.
    
    **IMPORTANT**: This tool automatically gets the current project and returns its full details including description.
    You do NOT need to call `get_current_project` first - this tool handles that internally.
    
    Returns:
        JSON string with current project details including:
        - id, name, description, status, priority
        - start_date, end_date, owner_id
        - created_at, updated_at
        - project_id: The full composite ID (provider_id:project_id)
        - provider_id: The PM provider UUID
        - provider_type: Type of provider (openproject, jira, etc.)
        
    If no project is currently selected, returns an error message asking the user to select a project.
    """
    try:
        # First, get the current project ID
        composite_project_id = get_current_project_id()
        
        if not composite_project_id:
            return json.dumps({
                "success": False,
                "error": "No project is currently selected. You MUST ask the user to provide a project ID or select one from the UI.",
                "has_project": False
            }, indent=2)
        
        # Now get the full project details
        handler = _ensure_pm_handler()
        
        # Handle provider_id:project_id format for multi-provider mode
        if ":" in composite_project_id:
            parts = composite_project_id.split(":", 1)
            provider_id = parts[0]
            actual_project_id = parts[1]
        else:
            actual_project_id = composite_project_id
            provider_id = None
        
        # Try to get project from provider directly
        project = None
        if handler.single_provider:
            project_obj = await handler.single_provider.get_project(actual_project_id)
            if project_obj:
                # Helper to safely get attribute or dict key
                def get_attr(obj, attr, default=None):
                    if isinstance(obj, dict):
                        return obj.get(attr, default)
                    return getattr(obj, attr, default)
                
                p_id = get_attr(project_obj, "id")
                p_name = get_attr(project_obj, "name")
                p_desc = get_attr(project_obj, "description") or ""
                p_status = get_attr(project_obj, "status")
                p_priority = get_attr(project_obj, "priority")
                p_start = get_attr(project_obj, "start_date")
                p_end = get_attr(project_obj, "end_date")
                p_owner = get_attr(project_obj, "owner_id")
                p_created = get_attr(project_obj, "created_at")
                p_updated = get_attr(project_obj, "updated_at")
                
                project = {
                    "id": str(p_id) if p_id else None,
                    "name": p_name,
                    "description": p_desc,
                    "status": str(p_status) if p_status else None,
                    "priority": str(p_priority) if p_priority else None,
                    "start_date": p_start.isoformat() if hasattr(p_start, 'isoformat') else str(p_start) if p_start else None,
                    "end_date": p_end.isoformat() if hasattr(p_end, 'isoformat') else str(p_end) if p_end else None,
                    "owner_id": str(p_owner) if p_owner else None,
                    "created_at": p_created.isoformat() if hasattr(p_created, 'isoformat') else str(p_created) if p_created else None,
                    "updated_at": p_updated.isoformat() if hasattr(p_updated, 'isoformat') else str(p_updated) if p_updated else None,
                    "project_id": composite_project_id,
                    "provider_id": provider_id,
                    "provider_type": getattr(handler.single_provider, 'provider_type', "unknown")
                }
        else:
            # List all and find matching
            projects = await handler.list_all_projects()
            project = next((p for p in projects if p.get('id') == composite_project_id), None)
            if project:
                project["project_id"] = composite_project_id
                project["provider_id"] = provider_id
        
        if not project:
            return json.dumps({
                "success": False,
                "error": f"Project not found: {composite_project_id}",
                "project_id": composite_project_id
            }, indent=2)
        
        return json.dumps(project, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error getting current project details: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


@tool
async def get_project(project_id: Annotated[str, "The project ID to retrieve"]) -> str:
    """Get details of a specific project by ID.
    
    Args:
        project_id: The ID of the project to retrieve
        
    Returns:
        JSON string with project details including:
        - id, name, description, status, priority
        - start_date, end_date, owner_id
        - created_at, updated_at
    """
    try:
        handler = _ensure_pm_handler()
        
        # Handle provider_id:project_id format for multi-provider mode
        if ":" in project_id:
            parts = project_id.split(":", 1)
            provider_id = parts[0]
            actual_project_id = parts[1]
        else:
            actual_project_id = project_id
        
        # Try to get project from provider directly
        project = None
        if handler.single_provider:
            project_obj = await handler.single_provider.get_project(actual_project_id)
            if project_obj:
                project = {
                    "id": str(project_obj.id),
                    "name": project_obj.name,
                    "description": project_obj.description or "",
                    "status": str(project_obj.status) if project_obj.status else None,
                    "priority": str(project_obj.priority) if project_obj.priority else None,
                    "start_date": project_obj.start_date.isoformat() if project_obj.start_date else None,
                    "end_date": project_obj.end_date.isoformat() if project_obj.end_date else None,
                    "owner_id": str(project_obj.owner_id) if project_obj.owner_id else None,
                    "created_at": project_obj.created_at.isoformat() if project_obj.created_at else None,
                    "updated_at": project_obj.updated_at.isoformat() if project_obj.updated_at else None,
                }
        else:
            # List all and find matching
            projects = await handler.list_all_projects()
            project = next((p for p in projects if p.get('id') == project_id), None)
        
        if not project:
            return json.dumps({
                "success": False,
                "error": f"Project not found: {project_id}"
            })
        
        return json.dumps({
            "success": True,
            "project": project
        }, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error getting project {project_id}: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
async def list_tasks(
    project_id: Annotated[Optional[str], "Project ID (use the project from context if not specified)"] = None,
    assignee_id: Annotated[Optional[str], "Filter by assignee ID"] = None,
    sprint_id: Annotated[Optional[str], "Sprint number or ID to filter tasks (e.g., '6' for Sprint 6)"] = None
) -> str:
    """Retrieve tasks from the project management system. USE THIS TOOL IMMEDIATELY when user asks about tasks.
    
    WHEN TO USE THIS TOOL:
    - User asks "list tasks" or "show tasks" or "get tasks"
    - User asks about tasks in a specific sprint (e.g., "tasks in sprint 6")
    - User asks about task status, progress, or work items
    - User asks "what tasks are there" or similar
    
    IMPORTANT: Call this tool directly with parameters. Do NOT ask for clarification.
    The sprint_id can be a number like "6" - it will be resolved automatically.
    If project_id is not provided, the current project context will be used.
    
    Args:
        project_id: Project ID from context (usually pre-filled)
        assignee_id: Filter tasks by assignee
        sprint_id: Sprint number or ID (e.g., "6" means Sprint 6)
        
    Returns:
        JSON with task list including id, title, status, priority, assignee, dates
    """
    try:
        handler = _ensure_pm_handler()
        
        # Extract actual project ID if in provider_id:project_id format
        actual_project_id = None
        if project_id and ":" in project_id:
            actual_project_id = project_id.split(":", 1)[1]
        if project_id:
            actual_project_id = project_id
        else:
            # Auto-detect project ID if not provided, needed for Smart Resolution
            composite_project_id = get_current_project_id()
            if composite_project_id:
                if ":" in composite_project_id:
                    actual_project_id = composite_project_id.split(":", 1)[1]
                else:
                    actual_project_id = composite_project_id
        
        logger.info(f"[{get_ts()}] [PM-TOOLS] list_tasks ENTER - project_id='{project_id}', assignee_id='{assignee_id}', sprint_id='{sprint_id}'")
        logger.info(f"[{get_ts()}] [PM-TOOLS] list_tasks detected/actual project_id='{actual_project_id}'")

        # Extract sprint ID from composite format (e.g., "project_id:sprint_id" -> "sprint_id")
        actual_sprint_id = None
        if sprint_id:
            if ":" in sprint_id:
                # Format: "project_id:sprint_id" or "provider_id:project_id:sprint_id"
                parts = sprint_id.split(":")
                actual_sprint_id = parts[-1]  # Get last part (sprint_id)
            else:
                actual_sprint_id = sprint_id
        
        # Smart Resolution: If sprint_id looks like a name (e.g. "Sprint 4") or index (e.g. "4"), try to resolve it to an ID
        # Heuristic: Real IDs are usually 3+ digits.
        is_ambiguous = False
        if actual_sprint_id:
            if actual_sprint_id.isdigit() and len(actual_sprint_id) < 3:
                is_ambiguous = True # It's a small number like "4"
            elif not actual_sprint_id.isdigit():
                is_ambiguous = True # It's a string like "Sprint 4" (assuming real IDs are numeric strings in OpenProject)
        
        if is_ambiguous and actual_sprint_id and hasattr(handler, 'list_project_sprints') and actual_project_id:
            try:
                # Fetch sprints to resolve the name/index
                project_for_sprints = actual_project_id
                if ":" in project_for_sprints:
                   project_for_sprints = project_for_sprints.split(":", 1)[1]
                
                logger.info(f"[PM-TOOLS] Smart Resolution: Resolving ambiguous sprint_id='{actual_sprint_id}' for project='{project_for_sprints}'")
                sprints = await handler.list_project_sprints(project_for_sprints)
                
                resolved_id = None
                # Strategy 1: Exact Name Match (Case Insensitive)
                for s in sprints:
                    if s.get("name") and s.get("name").lower() == actual_sprint_id.lower():
                        resolved_id = str(s.get("id"))
                        logger.info(f"[PM-TOOLS] Smart Resolution: Matched Name '{s.get('name')}' -> ID {resolved_id}")
                        break
                
                # Strategy 2: "Sprint X" Pattern Match (if input is "4", look for "Sprint 4")
                if not resolved_id and actual_sprint_id.isdigit():
                    target_name = f"Sprint {actual_sprint_id}"
                    for s in sprints:
                        if s.get("name") and s.get("name").lower() == target_name.lower():
                            resolved_id = str(s.get("id"))
                            logger.info(f"[PM-TOOLS] Smart Resolution: Matched Pattern '{target_name}' -> ID {resolved_id}")
                            break

                if resolved_id:
                    actual_sprint_id = resolved_id
                else:
                    logger.warning(f"[PM-TOOLS] Smart Resolution: Could not resolve '{actual_sprint_id}'")
            except Exception as e:
                logger.warning(f"[PM-TOOLS] Smart Resolution Failed: {e}")

        if actual_sprint_id and actual_sprint_id.isdigit() and len(actual_sprint_id) < 3:
             # Heuristic: IDs are usually 3+ digits. Sprint numbers are 1-2 digits.
             # This prevents the agent from hallucinating IDs.
             return json.dumps({
                 "success": False,
                 "error": f"Invalid sprint_id '{actual_sprint_id}'. It appears to be a sprint number, not an ID. Please call 'list_sprints' first to find the real ID (e.g. '613') and use that."
             })

        logger.info(f"[{get_ts()}] [PM-TOOLS] list_tasks: Filter strategy check - sprint_id='{actual_sprint_id}', project_id='{actual_project_id}'")
        
        # If sprint_id is provided, try to use a more efficient method
        # Check if handler has a method to get tasks by sprint directly
        if actual_sprint_id and hasattr(handler, 'list_project_tasks'):
            try:
                # Try to get tasks for the project and filter by sprint_id at the provider level
                # This is more efficient than listing all tasks
                if actual_project_id:
                    # Extract project_id from composite format if needed
                    project_for_tasks = actual_project_id
                    if ":" in project_for_tasks:
                        project_for_tasks = project_for_tasks.split(":", 1)[1]
                    
                    # Use list_project_tasks which may be more efficient
                    tasks = await handler.list_project_tasks(project_for_tasks)
                    # Filter by sprint_id
                    original_count = len(tasks)
                    tasks = [
                        t for t in tasks 
                        if t.get("sprint_id") and str(t.get("sprint_id")) == str(actual_sprint_id)
                    ]
                    logger.info(
                        f"[PM-TOOLS] list_tasks: Used list_project_tasks and filtered by sprint_id={actual_sprint_id}: "
                        f"{original_count} → {len(tasks)} tasks"
                    )
                else:
                    # No project_id, fall back to list_all_tasks
                    tasks = await handler.list_all_tasks(
                        project_id=actual_project_id,
                        assignee_id=assignee_id
                    )
                    # Filter by sprint_id
                    original_count = len(tasks)
                    tasks = [
                        t for t in tasks 
                        if t.get("sprint_id") and str(t.get("sprint_id")) == str(actual_sprint_id)
                    ]
                    logger.info(
                        f"[PM-TOOLS] list_tasks: Filtered by sprint_id={actual_sprint_id}: "
                        f"{original_count} → {len(tasks)} tasks"
                    )
            except Exception as e:
                logger.warning(
                    f"[PM-TOOLS] list_tasks: Error using list_project_tasks, falling back to list_all_tasks: {e}"
                )
                # Fall back to list_all_tasks
                tasks = await handler.list_all_tasks(
                    project_id=actual_project_id,
                    assignee_id=assignee_id
                )
                # Filter by sprint_id
                if actual_sprint_id:
                    original_count = len(tasks)
                    tasks = [
                        t for t in tasks 
                        if t.get("sprint_id") and str(t.get("sprint_id")) == str(actual_sprint_id)
                    ]
                    logger.info(
                        f"[PM-TOOLS] list_tasks: Filtered by sprint_id={actual_sprint_id}: "
                        f"{original_count} → {len(tasks)} tasks"
                    )
        else:
            # No sprint_id filter, use standard method
            tasks = await handler.list_all_tasks(
                project_id=actual_project_id,
                assignee_id=assignee_id
            )
            
            # Filter by sprint_id if provided (fallback for when list_project_tasks not available)
            if actual_sprint_id:
                original_count = len(tasks)
                # Try multiple sprint_id formats for matching:
                # 1. Exact match: "613"
                # 2. Composite format: "478:613" or "project_id:613"
                # 3. Provider format: "provider_id:project_id:613"
                matching_tasks = []
                for t in tasks:
                    task_sprint_id = t.get("sprint_id")
                    if not task_sprint_id:
                        continue
                    
                    task_sprint_id_str = str(task_sprint_id)
                    # Try exact match first
                    if task_sprint_id_str == str(actual_sprint_id):
                        matching_tasks.append(t)
                    # Try matching last part of composite sprint_id (e.g., "478:613" -> "613")
                    elif ":" in task_sprint_id_str:
                        sprint_parts = task_sprint_id_str.split(":")
                        if sprint_parts[-1] == str(actual_sprint_id):
                            matching_tasks.append(t)
                    # Try matching if actual_sprint_id is composite and task has just the sprint part
                    elif ":" in str(actual_sprint_id):
                        actual_parts = str(actual_sprint_id).split(":")
                        if task_sprint_id_str == actual_parts[-1]:
                            matching_tasks.append(t)
                
                tasks = matching_tasks
                logger.info(
                    f"[PM-TOOLS] list_tasks: Filtered by sprint_id={actual_sprint_id}: "
                    f"{original_count} → {len(tasks)} tasks"
                )
        
        
        logger.info(f"[{get_ts()}] [PM-TOOLS] list_tasks: Returning {len(tasks)} tasks")
        if tasks:
            task_ids = [t.get("id") for t in tasks]
            logger.info(f"[{get_ts()}] [PM-TOOLS] list_tasks: Task IDs: {task_ids}")
            # Log first task for debugging
            logger.info(f"[{get_ts()}] [PM-TOOLS] list_tasks: First task sample: {json.dumps(tasks[0], default=str)[:200]}...")
            
        result = json.dumps({
            "success": True,
            "tasks": tasks,
            "count": len(tasks)
        }, indent=2, default=str)
        
        # LAZY OPTIMIZATION: Do NOT truncate at tool level.
        # Let the context manager at reporter level handle limits ONLY if exceeded.
        # This preserves full task data for simple queries.
        logger.info(f"[{get_ts()}] [PM-TOOLS] list_tasks returning {len(result):,} chars (≈{len(result)//4:,} tokens) - NO TRUNCATION at tool level")
        
        return result
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
async def list_my_tasks() -> str:
    """List tasks assigned to the current user across all PM providers.
    
    This tool queries all active PM providers (OpenProject, JIRA, ClickUp, etc.)
    and returns all tasks assigned to the current authenticated user.
    
    Returns:
        JSON string with list of tasks assigned to current user, each containing:
        - id, title, description, status, priority
        - project_id, project_name, assignee_id, sprint_id, epic_id
        - estimated_hours, actual_hours
        - start_date, due_date, completed_at
        - provider_id: The provider ID for tasks from multi-provider setups
    """
    try:
        handler = _ensure_pm_handler()
        
        # Use handler method which handles both single and multi-provider modes
        tasks = await handler.list_my_tasks()
        result = json.dumps({
            "success": True,
            "tasks": tasks,
            "count": len(tasks)
        }, indent=2, default=str)
        
        # CRITICAL: Truncate large results to prevent token overflow in ReAct agent scratchpad
        from backend.utils.json_utils import sanitize_tool_response
        max_chars = 4000  # 1000 tokens * 4 chars/token
        if len(result) > max_chars:
            logger.warning(
                f"[PM-TOOLS] list_my_tasks returned {len(result):,} chars "
                f"(≈{len(result)//4:,} tokens). Truncating to {max_chars:,} chars."
            )
            result = sanitize_tool_response(result, max_length=max_chars, compress_arrays=True)
            logger.info(f"[PM-TOOLS] ✅ list_my_tasks truncated to {len(result):,} chars (≈{len(result)//4:,} tokens)")
        
        return result
    except Exception as e:
        logger.error(f"Error listing my tasks: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
async def get_task(task_id: Annotated[str, "The task ID to retrieve"]) -> str:
    """Get details of a specific task by ID.
    
    Args:
        task_id: The ID of the task to retrieve
        
    Returns:
        JSON string with task details including:
        - id, title, description, status, priority
        - project_id, assignee_id, sprint_id, epic_id
        - component_ids, label_ids
        - estimated_hours, actual_hours
        - start_date, due_date, completed_at
    """
    try:
        handler = _ensure_pm_handler()
        
        # Handle provider_id:task_id format
        if ":" in task_id:
            parts = task_id.split(":", 1)
            provider_id = parts[0]
            actual_task_id = parts[1]
        else:
            actual_task_id = task_id
        
        # Try to get task from provider directly
        task = None
        if handler.single_provider:
            task_obj = await handler.single_provider.get_task(actual_task_id)
            if task_obj:
                task = {
                    "id": str(task_obj.id),
                    "title": task_obj.title,
                    "description": task_obj.description or "",
                    "status": str(task_obj.status) if task_obj.status else None,
                    "priority": str(task_obj.priority) if task_obj.priority else None,
                    "project_id": str(task_obj.project_id) if task_obj.project_id else None,
                    "assignee_id": str(task_obj.assignee_id) if task_obj.assignee_id else None,
                    "sprint_id": str(task_obj.sprint_id) if task_obj.sprint_id else None,
                    "epic_id": str(task_obj.epic_id) if task_obj.epic_id else None,
                    "estimated_hours": task_obj.estimated_hours,
                    "actual_hours": task_obj.actual_hours,
                    "start_date": task_obj.start_date.isoformat() if task_obj.start_date else None,
                    "due_date": task_obj.due_date.isoformat() if task_obj.due_date else None,
                    "completed_at": task_obj.completed_at.isoformat() if task_obj.completed_at else None,
                }
        else:
            # List all and find matching
            tasks = await handler.list_all_tasks()
            task = next((t for t in tasks if t.get('id') == task_id), None)
        
        if not task:
            return json.dumps({
                "success": False,
                "error": f"Task not found: {task_id}"
            })
        
        return json.dumps({
            "success": True,
            "task": task
        }, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
async def list_sprints(
    project_id: Annotated[Optional[str], "Optional project ID. If not provided, uses the currently selected project."] = None
) -> str:
    """List sprints from the PM provider.
    
    If `project_id` is not provided, it will automatically use the currently selected project.
    
    Args:
        project_id: Optional. The ID of the project to list sprints for.
        
    Returns:
        JSON string with list of sprints.
    """
    try:
        handler = _ensure_pm_handler()
        
        # Auto-detect project ID if not provided
        if not project_id:
            project_id = get_current_project_id()
            if not project_id:
                 return json.dumps({
                    "success": False,
                    "error": "No project selected. Please provide a project_id or select a project."
                })
        
        # Extract actual project ID if in provider_id:project_id format
        actual_project_id = project_id
        if project_id and ":" in project_id:
            actual_project_id = project_id.split(":", 1)[1]
            
        
        # Use handler method if available, otherwise use provider directly
        sprints = []
        handler_type = handler.__class__.__name__
        logger.info(f"[PM-TOOLS] list_sprints: Using handler type: {handler_type}, project_id: {actual_project_id}")

        import time
        start_time = time.time()
        
        # Use handler method which handles both single and multi-provider modes
        if handler.single_provider:
             sprints = await handler.single_provider.list_project_sprints(actual_project_id)
        else:
             sprints = await handler.list_all_sprints(project_id=actual_project_id)
             
        duration = time.time() - start_time
        logger.info(f"[PM-TOOLS] ⏱️ END list_sprints - took {duration:.2f}s, found {len(sprints)} sprints")
        
        if hasattr(handler, 'list_all_sprints'):
            logger.info(f"[PM-TOOLS] list_sprints: Calling handler.list_all_sprints(project_id={actual_project_id})")
            sprints = await handler.list_all_sprints(project_id=actual_project_id)
            logger.info(f"[PM-TOOLS] list_sprints: handler.list_all_sprints returned {len(sprints)} sprints")
        elif handler.single_provider:
            logger.info(f"[PM-TOOLS] list_sprints: Using single_provider.list_sprints(project_id={actual_project_id})")
            sprint_objs = await handler.single_provider.list_sprints(project_id=actual_project_id)
            logger.info(f"[PM-TOOLS] list_sprints: single_provider.list_sprints returned {len(sprint_objs)} sprint objects")
            sprints = [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "project_id": str(s.project_id) if s.project_id else None,
                    "status": str(s.status) if s.status else None,
                    "start_date": s.start_date.isoformat() if s.start_date else None,
                    "end_date": s.end_date.isoformat() if s.end_date else None,
                    "capacity_hours": s.capacity_hours,
                    "planned_hours": s.planned_hours,
                    "goal": s.goal or "",
                }
                for s in sprint_objs
            ]
        elif project_id:
            logger.info(f"[PM-TOOLS] list_sprints: Calling handler.list_project_sprints(project_id={project_id})")
            sprints = await handler.list_project_sprints(project_id)
            logger.info(f"[PM-TOOLS] list_sprints: handler.list_project_sprints returned {len(sprints)} sprints")
        
        # INVESTIGATE: Check for duplicate sprint IDs to understand why list is doubled
        sprint_ids = [s.get("id") if isinstance(s, dict) else str(getattr(s, "id", None)) for s in sprints]
        unique_ids = set(sprint_ids)
        if len(sprint_ids) != len(unique_ids):
            duplicate_count = len(sprint_ids) - len(unique_ids)
            logger.warning(
                f"[PM-TOOLS] ⚠️ DUPLICATE SPRINTS DETECTED: {len(sprint_ids)} total sprints, "
                f"{len(unique_ids)} unique IDs, {duplicate_count} duplicates found!"
            )
            # Log which IDs are duplicated
            from collections import Counter
            id_counts = Counter(sprint_ids)
            duplicates = {id: count for id, count in id_counts.items() if count > 1}
            logger.warning(f"[PM-TOOLS] Duplicate sprint IDs: {duplicates}")
            # Log first few sprint IDs to see pattern
            logger.info(f"[PM-TOOLS] First 10 sprint IDs: {sprint_ids[:10]}")
        else:
            logger.info(f"[PM-TOOLS] ✅ No duplicates: {len(sprint_ids)} sprints, all unique IDs")
        
        # TEMPORARY: Deduplicate sprints by ID to prevent duplicates from PM service
        # TODO: Remove this once root cause is fixed
        seen_ids = set()
        deduplicated_sprints = []
        for sprint in sprints:
            sprint_id = sprint.get("id") if isinstance(sprint, dict) else None
            if sprint_id and sprint_id not in seen_ids:
                seen_ids.add(sprint_id)
                deduplicated_sprints.append(sprint)
            elif sprint_id:
                logger.warning(f"[PM-TOOLS] Removing duplicate sprint (ID: {sprint_id})")
        
        if len(deduplicated_sprints) < len(sprints):
            logger.warning(
                f"[PM-TOOLS] ⚠️ Deduplicated sprints: {len(sprints)} → {len(deduplicated_sprints)} "
                f"(removed {len(sprints) - len(deduplicated_sprints)} duplicates) - "
                f"THIS IS A WORKAROUND, ROOT CAUSE NEEDS INVESTIGATION"
            )
        
        sprints = deduplicated_sprints
        
        result = json.dumps({
            "success": True,
            "sprints": sprints,
            "count": len(sprints)
        }, indent=2, default=str)
        
        # CRITICAL: Truncate large results to prevent token overflow in ReAct agent scratchpad
        from backend.utils.json_utils import sanitize_tool_response
        max_chars = 4000  # 1000 tokens * 4 chars/token
        if len(result) > max_chars:
            logger.warning(
                f"[PM-TOOLS] list_sprints returned {len(result):,} chars "
                f"(≈{len(result)//4:,} tokens). Truncating to {max_chars:,} chars."
            )
            result = sanitize_tool_response(result, max_length=max_chars, compress_arrays=True)
            logger.info(f"[PM-TOOLS] ✅ list_sprints truncated to {len(result):,} chars (≈{len(result)//4:,} tokens)")
        
        return result
    except Exception as e:
        logger.error(f"Error listing sprints: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
async def get_sprint(sprint_id: Annotated[str, "The sprint ID to retrieve"]) -> str:
    """Get details of a specific sprint by ID.
    
    Args:
        sprint_id: The ID of the sprint to retrieve
        
    Returns:
        JSON string with sprint details including:
        - id, name, project_id, status
        - start_date, end_date
        - capacity_hours, planned_hours
        - goal, created_at, updated_at
    """
    try:
        handler = _ensure_pm_handler()
        
        # Handle provider_id:sprint_id format
        if ":" in sprint_id:
            parts = sprint_id.split(":", 1)
            provider_id = parts[0]
            actual_sprint_id = parts[1]
        else:
            actual_sprint_id = sprint_id
        
        # Try to get sprint from provider directly
        sprint = None
        if handler.single_provider:
            sprint_obj = await handler.single_provider.get_sprint(actual_sprint_id)
            if sprint_obj:
                sprint = {
                    "id": str(sprint_obj.id),
                    "name": sprint_obj.name,
                    "project_id": str(sprint_obj.project_id) if sprint_obj.project_id else None,
                    "status": str(sprint_obj.status) if sprint_obj.status else None,
                    "start_date": sprint_obj.start_date.isoformat() if sprint_obj.start_date else None,
                    "end_date": sprint_obj.end_date.isoformat() if sprint_obj.end_date else None,
                    "capacity_hours": sprint_obj.capacity_hours,
                    "planned_hours": sprint_obj.planned_hours,
                    "goal": sprint_obj.goal or "",
                }
        else:
            # List all and find matching - need to iterate through projects
            projects = await handler.list_all_projects()
            for project in projects:
                project_id = project.get('id')
                if project_id:
                    sprints = await handler.list_project_sprints(project_id)
                    sprint = next((s for s in sprints if s.get('id') == sprint_id), None)
                    if sprint:
                        break
        
        if not sprint:
            return json.dumps({
                "success": False,
                "error": f"Sprint not found: {sprint_id}"
            })
        
        return json.dumps({
            "success": True,
            "sprint": sprint
        }, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error getting sprint {sprint_id}: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
async def list_epics(
    project_id: Annotated[Optional[str], "Optional project ID to filter epics"] = None
) -> str:
    """List epics from the PM provider.
    
    Args:
        project_id: Optional project ID to filter epics by project
        
    Returns:
        JSON string with list of epics, each containing:
        - id, name, description, project_id
        - status, priority
        - start_date, end_date, owner_id
        - created_at, updated_at
    """
    try:
        handler = _ensure_pm_handler()
        
        # Extract actual project ID if in provider_id:project_id format
        actual_project_id = None
        if project_id and ":" in project_id:
            actual_project_id = project_id.split(":", 1)[1]
        elif project_id:
            actual_project_id = project_id
        
        # Use handler method if available, otherwise use provider directly
        epics = []
        if hasattr(handler, 'list_all_epics'):
            epics = await handler.list_all_epics(project_id=actual_project_id)
        elif handler.single_provider:
            epic_objs = await handler.single_provider.list_epics(project_id=actual_project_id)
            epics = [
                {
                    "id": str(e.id),
                    "name": e.name,
                    "description": e.description or "",
                    "project_id": str(e.project_id) if e.project_id else None,
                    "status": str(e.status) if e.status else None,
                    "priority": str(e.priority) if e.priority else None,
                    "start_date": e.start_date.isoformat() if e.start_date else None,
                    "end_date": e.end_date.isoformat() if e.end_date else None,
                    "owner_id": str(e.owner_id) if e.owner_id else None,
                }
                for e in epic_objs
            ]
        elif project_id:
            epics = await handler.list_project_epics(project_id)
        
        return json.dumps({
            "success": True,
            "epics": epics,
            "count": len(epics)
        }, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error listing epics: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
async def get_epic(epic_id: Annotated[str, "The epic ID to retrieve"]) -> str:
    """Get details of a specific epic by ID.
    
    Args:
        epic_id: The ID of the epic to retrieve
        
    Returns:
        JSON string with epic details including:
        - id, name, description, project_id
        - status, priority
        - start_date, end_date, owner_id
        - created_at, updated_at
    """
    try:
        handler = _ensure_pm_handler()
        
        # Handle provider_id:epic_id format
        if ":" in epic_id:
            parts = epic_id.split(":", 1)
            provider_id = parts[0]
            actual_epic_id = parts[1]
        else:
            actual_epic_id = epic_id
        
        # Try to get epic from provider directly
        epic = None
        if handler.single_provider:
            epic_obj = await handler.single_provider.get_epic(actual_epic_id)
            if epic_obj:
                epic = {
                    "id": str(epic_obj.id),
                    "name": epic_obj.name,
                    "description": epic_obj.description or "",
                    "project_id": str(epic_obj.project_id) if epic_obj.project_id else None,
                    "status": str(epic_obj.status) if epic_obj.status else None,
                    "priority": str(epic_obj.priority) if epic_obj.priority else None,
                    "start_date": epic_obj.start_date.isoformat() if epic_obj.start_date else None,
                    "end_date": epic_obj.end_date.isoformat() if epic_obj.end_date else None,
                    "owner_id": str(epic_obj.owner_id) if epic_obj.owner_id else None,
                }
        else:
            # List all and find matching - need to iterate through projects
            projects = await handler.list_all_projects()
            for project in projects:
                project_id = project.get('id')
                if project_id:
                    epics = await handler.list_project_epics(project_id)
                    epic = next((e for e in epics if e.get('id') == epic_id), None)
                    if epic:
                        break
        
        if not epic:
            return json.dumps({
                "success": False,
                "error": f"Epic not found: {epic_id}"
            })
        
        return json.dumps({
            "success": True,
            "epic": epic
        }, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error getting epic {epic_id}: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
async def list_users(
    project_id: Annotated[Optional[str], "Optional project ID to filter users"] = None
) -> str:
    """List users/members from the PM provider.
    
    Args:
        project_id: Optional project ID to filter users by project membership
        
    Returns:
        JSON string with list of users, each containing:
        - id, name, email, username
        - avatar_url (if available)
    """
    try:
        handler = _ensure_pm_handler()
        
        # Extract actual project ID if in provider_id:project_id format
        actual_project_id = None
        if project_id and ":" in project_id:
            actual_project_id = project_id.split(":", 1)[1]
        elif project_id:
            actual_project_id = project_id
        
        # Use provider directly to list users
        users = []
        if handler.single_provider:
            user_objs = await handler.single_provider.list_users(project_id=actual_project_id)
            # Handle both dict and object responses
            for u in user_objs:
                if isinstance(u, dict):
                    users.append({
                        "id": str(u.get("id", "")),
                        "name": u.get("name", ""),
                        "email": u.get("email", ""),
                        "username": u.get("username", ""),
                        "avatar_url": u.get("avatar_url", ""),
                    })
                else:
                    users.append({
                        "id": str(u.id),
                        "name": u.name,
                        "email": u.email or "",
                        "username": u.username or "",
                        "avatar_url": u.avatar_url or "",
                    })
        
        return json.dumps({
            "success": True,
            "users": users,
            "count": len(users)
        }, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
async def get_current_user() -> str:
    """Get the current authenticated user from the PM provider.
    
    Returns:
        JSON string with current user details including:
        - id, name, email, username
        - avatar_url (if available)
    """
    try:
        handler = _ensure_pm_handler()
        
        # In single-provider mode, get current user from provider
        if handler.single_provider:
            user = await handler.single_provider.get_current_user()
            if user:
                user_dict = {
                    "id": str(user.id) if user.id else None,
                    "name": user.name,
                    "email": user.email or "",
                    "username": user.username or "",
                    "avatar_url": user.avatar_url or "",
                }
                return json.dumps({
                    "success": True,
                    "user": user_dict
                }, indent=2)
        
        return json.dumps({
            "success": False,
            "error": "Current user not available"
        })
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def get_pm_tools() -> List:
    """Get list of all PM tools.
    
    Returns:
        List of PM tool instances
    """
    return [
        get_current_project,  # FIRST: Get current project context
        get_current_project_details,  # Get current project details including description (calls get_current_project internally)
        list_projects,
        get_project,
        list_tasks,
        list_my_tasks,
        get_task,
        list_sprints,
        get_sprint,
        list_epics,
        get_epic,
        list_users,
        get_current_user,
    ]
