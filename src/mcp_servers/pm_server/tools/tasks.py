"""
Task Management Tools

MCP tools for task operations across all PM providers.
"""

import logging
from typing import Any

from mcp.server import Server
from mcp.types import TextContent

from src.server.pm_handler import PMHandler
from ..config import PMServerConfig

logger = logging.getLogger(__name__)

# Enable debug logging for this module
_debug_logger = logging.getLogger("src.mcp_servers.pm_server.tools.tasks")


def register_task_tools(
    server: Server,
    pm_handler: PMHandler,
    config: PMServerConfig,
    tool_names: list[str] | None = None
) -> int:
    """
    Register task-related MCP tools.
    
    Args:
        server: MCP server instance
        pm_handler: PM handler for multi-provider operations
        config: Server configuration
    
    Returns:
        Number of tools registered
    """
    tool_count = 0
    
    # Tool 1: list_my_tasks
    @server.call_tool()
    async def list_my_tasks(arguments: dict[str, Any]) -> list[TextContent]:
        """
        List tasks assigned to the current user.
        
        This tool automatically:
        1. Lists all active PM providers
        2. Gets the current user for each provider (via get_current_user())
        3. Fetches all tasks assigned to that user (via list_tasks(assignee_id=current_user.id))
        4. Optionally filters by project if project_id is provided
        
        CONTEXT-AWARE BEHAVIOR:
        - If project_id is provided (from UI context or user request):
          → List tasks assigned to current user IN THAT SPECIFIC PROJECT
          → This is the expected behavior when user is working in a project context
          → Example: User selected "Project X" in UI, asks "list my tasks" → should show tasks in Project X
        
        - If project_id is NOT provided:
          → List ALL tasks assigned to current user across ALL projects and ALL providers
          → This is for when user wants to see everything, not filtered by project
        
        EXTRACTING PROJECT_ID FROM MESSAGE:
        If the user message contains "project_id: xxx" (injected by frontend), extract it and use it.
        The project_id can be in format "provider_id:project_id" or just "project_id".
        
        Args:
            project_id (optional): Filter by project ID. 
                                  - If provided: Returns tasks assigned to current user in that project only
                                  - If not provided: Returns all tasks assigned to current user across all projects
                                  Format: "provider_id:project_id" or just "project_id"
                                  Can also be extracted from message context if message contains "project_id: xxx"
            status (optional): Filter by status (e.g., "open", "in_progress", "done")
            provider_id (optional): Filter by provider
            limit (optional): Maximum number of tasks
        
        Returns:
            List of user's tasks (filtered by project if project_id provided, otherwise all tasks)
        """
        try:
            logger.info("=" * 80)
            logger.info("[MCP-TOOL] list_my_tasks called")
            logger.info(f"[MCP-TOOL] Raw arguments: {arguments}")
            logger.info(f"[MCP-TOOL] Arguments type: {type(arguments)}")
            logger.info("=" * 80)
            
            # Validate arguments is a dict
            if not isinstance(arguments, dict):
                logger.error(f"[list_my_tasks] Invalid arguments type: {type(arguments)}, expected dict")
                return [TextContent(
                    type="text",
                    text=f"Error: Invalid arguments format. Expected dictionary, got {type(arguments).__name__}."
                )]
            
            # Extract and validate parameters
            project_id = arguments.get("project_id")
            status = arguments.get("status")
            provider_id = arguments.get("provider_id")
            limit = arguments.get("limit")
            
            logger.info(f"[MCP-TOOL] Extracted parameters:")
            logger.info(f"  - project_id: {project_id} (type: {type(project_id)})")
            logger.info(f"  - status: {status}")
            logger.info(f"  - provider_id: {provider_id}")
            logger.info(f"  - limit: {limit}")
            
            # Normalize project_id if provided
            if project_id is not None:
                if not isinstance(project_id, str):
                    project_id = str(project_id)
                project_id = project_id.strip()
                if not project_id:
                    project_id = None
            
            # Normalize other parameters
            if status is not None and not isinstance(status, str):
                status = str(status).strip() if status else None
            if provider_id is not None and not isinstance(provider_id, str):
                provider_id = str(provider_id).strip() if provider_id else None
            if limit is not None:
                try:
                    limit = int(limit)
                except (ValueError, TypeError):
                    logger.warning(f"[list_my_tasks] Invalid limit value: {limit}, ignoring")
                    limit = None
            
            logger.info(
                f"list_my_tasks called: project_id={project_id}, status={status}, "
                f"provider_id={provider_id}, limit={limit}"
            )
            
            # Log when project_id is provided - this is expected when user is in project context
            if project_id:
                logger.info(
                    f"[list_my_tasks] project_id={project_id} provided. "
                    f"Filtering tasks to current user's tasks in this project."
                )
            
            logger.debug(
                f"[list_my_tasks] Starting task retrieval. "
                f"PMHandler mode: {pm_handler._mode}, "
                f"Will filter by project_id: {bool(project_id)}, "
                f"Will filter by provider_id: {bool(provider_id)}"
            )
            
            # Get tasks from PM handler (gets all tasks assigned to current user)
            # Note: PMHandler.list_my_tasks() doesn't accept parameters - it gets tasks from all providers
            # It works by:
            # 1. Listing all active PM providers
            # 2. For each provider, calling get_current_user() to get the current user
            # 3. Then calling list_tasks(assignee_id=current_user.id) to get tasks assigned to that user
            try:
                logger.info("=" * 80)
                logger.info("[MCP-TOOL] Calling pm_handler.list_my_tasks()...")
                logger.info(f"[MCP-TOOL] PMHandler mode: {pm_handler._mode}")
                logger.info("=" * 80)
                tasks = await pm_handler.list_my_tasks()
                logger.info("=" * 80)
                logger.info(f"[MCP-TOOL] Retrieved {len(tasks)} tasks from PMHandler")
                if tasks:
                    logger.info(f"[MCP-TOOL] Sample task project_ids: {[t.get('project_id') for t in tasks[:3]]}")
                logger.info("=" * 80)
            except Exception as e:
                logger.error(f"Error calling pm_handler.list_my_tasks(): {e}", exc_info=True)
                # Return error message but don't fail completely
                return [TextContent(
                    type="text",
                    text=f"Error retrieving tasks: {str(e)}\n\n"
                         "This might be due to:\n"
                         "- Sprint information that no longer exists\n"
                         "- Provider connection issues\n"
                         "- Missing permissions\n\n"
                         "Please try again or contact support if the issue persists."
                )]
            
            # Apply project_id filter if specified
            if project_id:
                logger.info("=" * 80)
                logger.info(f"[MCP-TOOL] Filtering {len(tasks)} tasks by project_id: {project_id}")
                logger.info(f"[MCP-TOOL] Project_id format check: contains ':' = {':' in project_id}")
                
                # Log sample task project_ids before filtering
                if tasks:
                    sample_project_ids = [t.get("project_id") for t in tasks[:5]]
                    logger.info(f"[MCP-TOOL] Sample task project_ids before filter: {sample_project_ids}")
                
                # Handle both formats: "provider_id:project_id" and just "project_id"
                if ":" in project_id:
                    # Format: "provider_id:project_id" - match exact project_id field
                    logger.info(f"[MCP-TOOL] Using exact match for project_id (contains ':')")
                    tasks = [t for t in tasks if t.get("project_id") == project_id]
                else:
                    # Format: just "project_id" - match if project_id ends with this or matches
                    logger.info(f"[MCP-TOOL] Using partial match for project_id (no ':')")
                    logger.info(f"[MCP-TOOL] Will match if task.project_id ends with ':{project_id}' or equals '{project_id}'")
                    original_count = len(tasks)
                    tasks = [
                        t for t in tasks
                        if str(t.get("project_id", "")).endswith(f":{project_id}")
                        or str(t.get("project_id", "")) == project_id
                        or str(t.get("project_id", "")).split(":")[-1] == project_id
                    ]
                    logger.info(f"[MCP-TOOL] Filtered from {original_count} to {len(tasks)} tasks")
                
                # Log sample task project_ids after filtering
                if tasks:
                    sample_project_ids = [t.get("project_id") for t in tasks[:5]]
                    logger.info(f"[MCP-TOOL] Sample task project_ids after filter: {sample_project_ids}")
                else:
                    logger.warning(f"[MCP-TOOL] No tasks matched project_id filter: {project_id}")
                    logger.warning(f"[MCP-TOOL] All task project_ids: {[t.get('project_id') for t in tasks[:10]]}")
                logger.info("=" * 80)
            
            # Apply provider_id filter if specified
            if provider_id:
                logger.debug(f"[list_my_tasks] Filtering {len(tasks)} tasks by provider_id: {provider_id}")
                tasks = [t for t in tasks if t.get("provider_id") == provider_id]
                logger.debug(f"[list_my_tasks] After provider_id filter: {len(tasks)} tasks remaining")
            
            # Apply status filter if specified
            if status:
                logger.debug(f"[list_my_tasks] Filtering {len(tasks)} tasks by status: {status}")
                status_lower = status.lower()
                tasks = [
                    t for t in tasks
                    if t.get("status", "").lower() == status_lower
                    or (status_lower == "open" and t.get("status", "").lower() not in ["done", "closed", "completed"])
                    or (status_lower == "done" and t.get("status", "").lower() in ["done", "closed", "completed"])
                ]
            
            # Apply limit
            if limit:
                logger.debug(f"[list_my_tasks] Limiting to {limit} tasks")
                tasks = tasks[:int(limit)]
            
            logger.debug(f"[list_my_tasks] Final result: {len(tasks)} tasks to return")
            
            if not tasks:
                return [TextContent(
                    type="text",
                    text="No tasks found."
                )]
            
            # Format output
            output_lines = [f"Found {len(tasks)} tasks:\n\n"]
            for i, task in enumerate(tasks, 1):
                # Use 'title' instead of 'subject' (PMHandler returns 'title')
                task_title = task.get('title') or task.get('subject', 'Untitled')
                task_id = task.get('id', 'N/A')
                task_status = task.get('status', 'N/A')
                project_name = task.get('project_name', 'N/A')
                assigned_to = task.get('assigned_to')
                sprint_id = task.get('sprint_id')
                
                output_lines.append(
                    f"{i}. **{task_title}** (ID: {task_id})\n"
                    f"   Status: {task_status} | "
                    f"Project: {project_name}\n"
                )
                if assigned_to:
                    output_lines.append(f"   Assigned to: {assigned_to}\n")
                if sprint_id:
                    output_lines.append(f"   Sprint ID: {sprint_id}\n")
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in list_my_tasks: {e}", exc_info=True)
            
            # Check if error is related to sprint lookup
            if "sprint" in error_msg.lower() and ("unavailable" in error_msg.lower() or "not found" in error_msg.lower() or "SCRUM" in error_msg):
                # This is likely a sprint validation error - tasks might reference non-existent sprints
                # Try to get tasks anyway, ignoring sprint validation errors
                logger.warning(f"Sprint-related error in list_my_tasks, but this shouldn't prevent task listing: {error_msg}")
                return [TextContent(
                    type="text",
                    text=f"⚠️ Warning: Some tasks reference sprints that are no longer available (e.g., SCRUM-1).\n\n"
                         f"Error details: {error_msg}\n\n"
                         "This usually happens when:\n"
                         "- Tasks are assigned to sprints that have been deleted\n"
                         "- Sprint IDs in tasks are outdated\n\n"
                         "The tasks themselves are still valid, but sprint information cannot be retrieved.\n"
                         "Please try again or contact support if the issue persists."
                )]
            
            return [TextContent(
                type="text",
                text=f"Error listing tasks: {error_msg}\n\n"
                     "This might be due to:\n"
                     "- Provider connection issues\n"
                     "- Missing permissions\n"
                     "- Invalid sprint or project references\n\n"
                     "Please try again or contact support if the issue persists."
            )]
    
    if tool_names is not None:
        tool_names.append("list_my_tasks")
    tool_count += 1
    
    # Tool 2: list_tasks
    @server.call_tool()
    async def list_tasks(arguments: dict[str, Any]) -> list[TextContent]:
        """
        List tasks in a project.
        
        Args:
            project_id (required): Project ID
            status (optional): Filter by status
            assignee (optional): Filter by assignee
            limit (optional): Maximum number of tasks
        
        Returns:
            List of tasks in the project
        """
        try:
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required"
                )]
            
            status = arguments.get("status")
            assignee = arguments.get("assignee")
            limit = arguments.get("limit")
            
            logger.info(
                f"list_tasks called: project_id={project_id}, status={status}"
            )
            
            # Get tasks from PM handler using list_project_tasks
            tasks = await pm_handler.list_project_tasks(project_id)
            
            # Apply filters
            if status:
                tasks = [t for t in tasks if t.get("status") == status]
            if assignee:
                tasks = [t for t in tasks if t.get("assignee_id") == assignee or t.get("assignee_name") == assignee]
            
            # Apply limit
            if limit:
                tasks = tasks[:int(limit)]
            
            if not tasks:
                return [TextContent(
                    type="text",
                    text=f"No tasks found in project {project_id}."
                )]
            
            # Format output
            output_lines = [f"Found {len(tasks)} tasks in project:\n\n"]
            for i, task in enumerate(tasks, 1):
                output_lines.append(
                    f"{i}. **{task.get('subject')}** (ID: {task.get('id')})\n"
                    f"   Status: {task.get('status', 'N/A')} | "
                    f"Assignee: {task.get('assignee_name', 'Unassigned')}\n"
                )
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in list_tasks: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error listing tasks: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("list_tasks")
    tool_count += 1
    
    # Tool 3: get_task
    @server.call_tool()
    async def get_task(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Get detailed information about a task.
        
        Args:
            task_id (required): Task ID
        
        Returns:
            Detailed task information
        """
        try:
            task_id = arguments.get("task_id")
            if not task_id:
                return [TextContent(
                    type="text",
                    text="Error: task_id is required"
                )]
            
            logger.info(f"get_task called: task_id={task_id}")
            
            # Get task by searching all projects
            # Extract project_id from task_id if in format "project_id:task_id"
            if ":" in task_id:
                project_id_part, task_id_part = task_id.split(":", 1)
                tasks = await pm_handler.list_project_tasks(project_id_part)
                task = next((t for t in tasks if str(t.get("id")) == task_id_part), None)
            else:
                # Search all projects
                all_tasks = await pm_handler.list_all_tasks()
                task = next((t for t in all_tasks if str(t.get("id")) == task_id), None)
            
            if not task:
                return [TextContent(
                    type="text",
                    text=f"Task with ID {task_id} not found."
                )]
            
            # Format detailed output
            output_lines = [
                f"# Task: {task.get('subject') or task.get('title', 'N/A')}\n\n",
                f"**ID:** {task.get('id')}\n",
                f"**Project:** {task.get('project_name', 'N/A')}\n",
                f"**Status:** {task.get('status', 'N/A')}\n",
                f"**Assignee:** {task.get('assignee_name', task.get('assigned_to', 'Unassigned'))}\n",
                f"**Priority:** {task.get('priority', 'N/A')}\n",
            ]
            
            if "description" in task and task["description"]:
                output_lines.append(f"\n**Description:**\n{task['description']}\n")
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in get_task: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error getting task: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("get_task")
    tool_count += 1
    
    # Tool 4: create_task
    @server.call_tool()
    async def create_task(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Create a new task.
        
        Args:
            project_id (required): Project ID
            subject (required): Task title
            description (optional): Task description
            assignee_id (optional): User ID to assign task to
            status (optional): Initial status
            priority (optional): Task priority
            due_date (optional): Due date (YYYY-MM-DD)
        
        Returns:
            Created task information
        """
        try:
            project_id = arguments.get("project_id")
            subject = arguments.get("subject")
            
            if not project_id or not subject:
                return [TextContent(
                    type="text",
                    text="Error: project_id and subject are required"
                )]
            
            logger.info(
                f"create_task called: project_id={project_id}, subject={subject}"
            )
            
            # Create task via PM handler using create_project_task
            task_data = {
                "subject": subject,
                "description": arguments.get("description"),
                "assignee_id": arguments.get("assignee_id"),
                "status": arguments.get("status"),
                "priority": arguments.get("priority"),
                "due_date": arguments.get("due_date")
            }
            task = await pm_handler.create_project_task(project_id, task_data)
            
            return [TextContent(
                type="text",
                text=f"✅ Task created successfully!\n\n"
                     f"**Subject:** {task.get('subject') or task.get('title', 'N/A')}\n"
                     f"**ID:** {task.get('id')}\n"
                     f"**Project:** {task.get('project_name', project_id)}\n"
            )]
            
        except Exception as e:
            logger.error(f"Error in create_task: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error creating task: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("create_task")
    tool_count += 1
    
    # Tool 5: update_task
    @server.call_tool()
    async def update_task(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Update an existing task.
        
        Args:
            task_id (required): Task ID
            subject (optional): New task title
            description (optional): New description
            status (optional): New status
            assignee_id (optional): New assignee
            priority (optional): New priority
            due_date (optional): New due date
        
        Returns:
            Updated task information
        """
        try:
            task_id = arguments.get("task_id")
            if not task_id:
                return [TextContent(
                    type="text",
                    text="Error: task_id is required"
                )]
            
            updates = {
                k: v for k, v in arguments.items()
                if k != "task_id" and v is not None
            }
            
            if not updates:
                return [TextContent(
                    type="text",
                    text="Error: At least one field to update is required"
                )]
            
            logger.info(
                f"update_task called: task_id={task_id}, updates={updates}"
            )
            
            # Task update is not yet fully implemented in PMHandler
            # For now, return a helpful message
            return [TextContent(
                type="text",
                text=f"Task update is not yet fully implemented. "
                     f"Please update tasks directly in your PM provider (JIRA, OpenProject, etc.). "
                     f"For assigning tasks, use assign_task_to_user API endpoint."
            )]
            
        except Exception as e:
            logger.error(f"Error in update_task: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error updating task: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("update_task")
    tool_count += 1
    
    # Tool 6: delete_task
    @server.call_tool()
    async def delete_task(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Delete a task.
        
        Args:
            task_id (required): Task ID
        
        Returns:
            Confirmation message
        """
        try:
            task_id = arguments.get("task_id")
            if not task_id:
                return [TextContent(
                    type="text",
                    text="Error: task_id is required"
                )]
            
            logger.info(f"delete_task called: task_id={task_id}")
            
            # Task deletion is not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Task deletion is not yet implemented. "
                     f"Please delete tasks directly in your PM provider (JIRA, OpenProject, etc.)."
            )]
            
        except Exception as e:
            logger.error(f"Error in delete_task: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error deleting task: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("delete_task")
    tool_count += 1
    
    # Tool 7: assign_task
    @server.call_tool()
    async def assign_task(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Assign a task to a user.
        
        Args:
            task_id (required): Task ID
            assignee_id (required): User ID to assign to
        
        Returns:
            Confirmation message
        """
        try:
            task_id = arguments.get("task_id")
            assignee_id = arguments.get("assignee_id")
            
            if not task_id or not assignee_id:
                return [TextContent(
                    type="text",
                    text="Error: task_id and assignee_id are required"
                )]
            
            logger.info(
                f"assign_task called: task_id={task_id}, assignee_id={assignee_id}"
            )
            
            # Extract project_id from task_id if in format "project_id:task_id"
            if ":" in task_id:
                project_id_part, task_id_part = task_id.split(":", 1)
            else:
                # Try to find project_id by searching all tasks
                all_tasks = await pm_handler.list_all_tasks()
                task = next((t for t in all_tasks if str(t.get("id")) == task_id), None)
                if task:
                    project_id_part = task.get("project_id", "").split(":")[0] if ":" in str(task.get("project_id", "")) else ""
                    task_id_part = task_id
                else:
                    return [TextContent(
                        type="text",
                        text=f"Task {task_id} not found. Cannot assign."
                    )]
            
            # Use assign_task_to_user method
            result = await pm_handler.assign_task_to_user(project_id_part, task_id_part, assignee_id)
            
            return [TextContent(
                type="text",
                text=f"✅ Task assigned successfully!\n\n"
                     f"**Task:** {result.get('subject', task_id)}\n"
                     f"**Assignee:** {result.get('assignee_name', assignee_id)}\n"
            )]
            
        except Exception as e:
            logger.error(f"Error in assign_task: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error assigning task: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("assign_task")
    tool_count += 1
    
    # Tool 8: update_task_status
    @server.call_tool()
    async def update_task_status(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Update task status.
        
        Args:
            task_id (required): Task ID
            status (required): New status
        
        Returns:
            Confirmation message
        """
        try:
            task_id = arguments.get("task_id")
            status = arguments.get("status")
            
            if not task_id or not status:
                return [TextContent(
                    type="text",
                    text="Error: task_id and status are required"
                )]
            
            logger.info(
                f"update_task_status called: task_id={task_id}, status={status}"
            )
            
            # Task status update is not yet fully implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Task status update is not yet fully implemented. "
                     f"Please update task status directly in your PM provider (JIRA, OpenProject, etc.)."
            )]
            
        except Exception as e:
            logger.error(f"Error in update_task_status: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error updating task status: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("update_task_status")
    tool_count += 1
    
    # Tool 9: search_tasks
    @server.call_tool()
    async def search_tasks(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Search tasks across projects.
        
        Args:
            query (required): Search query
            project_id (optional): Filter by project
            status (optional): Filter by status
            limit (optional): Maximum results
        
        Returns:
            List of matching tasks
        """
        try:
            query = arguments.get("query")
            if not query:
                return [TextContent(
                    type="text",
                    text="Error: query is required"
                )]
            
            project_id = arguments.get("project_id")
            status = arguments.get("status")
            limit = arguments.get("limit", 20)
            
            logger.info(
                f"search_tasks called: query={query}, project_id={project_id}"
            )
            
            # Search tasks by listing all tasks and filtering
            if project_id:
                tasks = await pm_handler.list_project_tasks(project_id)
            else:
                tasks = await pm_handler.list_all_tasks()
            
            # Apply search filter
            query_lower = query.lower()
            tasks = [
                t for t in tasks
                if query_lower in (t.get("subject") or t.get("title", "")).lower()
                or query_lower in (t.get("description") or "").lower()
            ]
            
            # Apply status filter
            if status:
                tasks = [t for t in tasks if t.get("status") == status]
            
            # Apply limit
            tasks = tasks[:int(limit)]
            
            if not tasks:
                return [TextContent(
                    type="text",
                    text=f"No tasks found matching '{query}'"
                )]
            
            output_lines = [f"Found {len(tasks)} tasks matching '{query}':\n\n"]
            for i, task in enumerate(tasks, 1):
                output_lines.append(
                    f"{i}. **{task.get('subject')}** (ID: {task.get('id')})\n"
                    f"   Project: {task.get('project_name')} | "
                    f"Status: {task.get('status')}\n"
                )
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in search_tasks: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error searching tasks: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("search_tasks")
    tool_count += 1
    
    logger.info(f"Registered {tool_count} task tools")
    return tool_count

