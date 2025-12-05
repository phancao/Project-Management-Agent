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
from typing import Annotated, Optional, List, Dict, Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# Global PM handler instance - will be set by conversation flow manager
_pm_handler = None


def set_pm_handler(handler):
    """Set the PM handler instance for tools to use"""
    global _pm_handler
    _pm_handler = handler
    logger.info(f"PM handler set for tools: {handler.__class__.__name__}")


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
        from src.utils.json_utils import sanitize_tool_response
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
    project_id: Annotated[Optional[str], "Optional project ID to filter tasks"] = None,
    assignee_id: Annotated[Optional[str], "Optional assignee ID to filter tasks"] = None
) -> str:
    """List tasks from the PM provider.
    
    Args:
        project_id: Optional project ID to filter tasks by project
        assignee_id: Optional assignee ID to filter tasks by assignee
        
    Returns:
        JSON string with list of tasks, each containing:
        - id, title, description, status, priority
        - project_id, assignee_id, sprint_id, epic_id
        - estimated_hours, actual_hours
        - start_date, due_date, completed_at
    """
    try:
        handler = _ensure_pm_handler()
        
        # Extract actual project ID if in provider_id:project_id format
        actual_project_id = None
        if project_id and ":" in project_id:
            actual_project_id = project_id.split(":", 1)[1]
        elif project_id:
            actual_project_id = project_id
        
        # Use handler method which handles both single and multi-provider modes
        tasks = await handler.list_all_tasks(
            project_id=actual_project_id,
            assignee_id=assignee_id
        )
        
        result = json.dumps({
            "success": True,
            "tasks": tasks,
            "count": len(tasks)
        }, indent=2, default=str)
        
        # CRITICAL: Truncate large results to prevent token overflow in ReAct agent scratchpad
        from src.utils.json_utils import sanitize_tool_response
        max_chars = 4000  # 1000 tokens * 4 chars/token
        if len(result) > max_chars:
            logger.warning(
                f"[PM-TOOLS] list_tasks returned {len(result):,} chars "
                f"(≈{len(result)//4:,} tokens). Truncating to {max_chars:,} chars."
            )
            result = sanitize_tool_response(result, max_length=max_chars, compress_arrays=True)
            logger.info(f"[PM-TOOLS] ✅ list_tasks truncated to {len(result):,} chars (≈{len(result)//4:,} tokens)")
        
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
        from src.utils.json_utils import sanitize_tool_response
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
    project_id: Annotated[Optional[str], "Optional project ID to filter sprints"] = None
) -> str:
    """List sprints from the PM provider.
    
    Args:
        project_id: Optional project ID to filter sprints by project
        
    Returns:
        JSON string with list of sprints, each containing:
        - id, name, project_id, status
        - start_date, end_date
        - capacity_hours, planned_hours
        - goal, created_at, updated_at
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
        sprints = []
        if hasattr(handler, 'list_all_sprints'):
            sprints = await handler.list_all_sprints(project_id=actual_project_id)
        elif handler.single_provider:
            sprint_objs = await handler.single_provider.list_sprints(project_id=actual_project_id)
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
            sprints = await handler.list_project_sprints(project_id)
        
        result = json.dumps({
            "success": True,
            "sprints": sprints,
            "count": len(sprints)
        }, indent=2, default=str)
        
        # CRITICAL: Truncate large results to prevent token overflow in ReAct agent scratchpad
        from src.utils.json_utils import sanitize_tool_response
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
            users = [
                {
                    "id": str(u.id),
                    "name": u.name,
                    "email": u.email or "",
                    "username": u.username or "",
                    "avatar_url": u.avatar_url or "",
                }
                for u in user_objs
            ]
        
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
