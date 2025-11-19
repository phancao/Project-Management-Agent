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


def register_task_tools(
    server: Server,
    pm_handler: PMHandler,
    config: PMServerConfig
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
        List tasks assigned to the current user across all providers.
        
        Args:
            status (optional): Filter by status (e.g., "open", "in_progress", "done")
            provider_id (optional): Filter by provider
            limit (optional): Maximum number of tasks
        
        Returns:
            List of user's tasks
        """
        try:
            status = arguments.get("status")
            provider_id = arguments.get("provider_id")
            limit = arguments.get("limit")
            
            logger.info(
                f"list_my_tasks called: status={status}, provider_id={provider_id}, limit={limit}"
            )
            
            # Get tasks from PM handler (gets all tasks assigned to current user)
            # Note: PMHandler.list_my_tasks() doesn't accept parameters - it gets tasks from all providers
            tasks = await pm_handler.list_my_tasks()
            
            # Apply provider_id filter if specified
            if provider_id:
                tasks = [t for t in tasks if t.get("provider_id") == provider_id]
            
            # Apply status filter if specified
            if status:
                status_lower = status.lower()
                tasks = [
                    t for t in tasks
                    if t.get("status", "").lower() == status_lower
                    or (status_lower == "open" and t.get("status", "").lower() not in ["done", "closed", "completed"])
                    or (status_lower == "done" and t.get("status", "").lower() in ["done", "closed", "completed"])
                ]
            
            # Apply limit
            if limit:
                tasks = tasks[:int(limit)]
            
            if not tasks:
                return [TextContent(
                    type="text",
                    text="No tasks found."
                )]
            
            # Format output
            output_lines = [f"Found {len(tasks)} tasks:\n\n"]
            for i, task in enumerate(tasks, 1):
                output_lines.append(
                    f"{i}. **{task.get('subject')}** (ID: {task.get('id')})\n"
                    f"   Status: {task.get('status', 'N/A')} | "
                    f"Project: {task.get('project_name', 'N/A')}\n"
                    f"   Provider: {task.get('provider_type')}\n"
                )
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in list_my_tasks: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error listing tasks: {str(e)}"
            )]
    
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
            
            # Get tasks from PM handler
            tasks = pm_handler.list_tasks(
                project_id=project_id,
                status=status,
                assignee=assignee
            )
            
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
            
            # Get task from PM handler
            task = pm_handler.get_task(task_id)
            
            if not task:
                return [TextContent(
                    type="text",
                    text=f"Task with ID {task_id} not found."
                )]
            
            # Format detailed output
            output_lines = [
                f"# Task: {task.get('subject')}\n\n",
                f"**ID:** {task.get('id')}\n",
                f"**Project:** {task.get('project_name', 'N/A')}\n",
                f"**Status:** {task.get('status', 'N/A')}\n",
                f"**Assignee:** {task.get('assignee_name', 'Unassigned')}\n",
                f"**Priority:** {task.get('priority', 'N/A')}\n",
                f"**Due Date:** {task.get('due_date', 'N/A')}\n",
                f"**Created:** {task.get('created_at', 'N/A')}\n",
                f"**Updated:** {task.get('updated_at', 'N/A')}\n",
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
            
            # Create task via PM handler
            task = pm_handler.create_task(
                project_id=project_id,
                subject=subject,
                description=arguments.get("description"),
                assignee_id=arguments.get("assignee_id"),
                status=arguments.get("status"),
                priority=arguments.get("priority"),
                due_date=arguments.get("due_date")
            )
            
            return [TextContent(
                type="text",
                text=f"✅ Task created successfully!\n\n"
                     f"**Subject:** {task.get('subject')}\n"
                     f"**ID:** {task.get('id')}\n"
                     f"**Project:** {task.get('project_name')}\n"
            )]
            
        except Exception as e:
            logger.error(f"Error in create_task: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error creating task: {str(e)}"
            )]
    
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
            
            # Update task via PM handler
            task = pm_handler.update_task(task_id, **updates)
            
            return [TextContent(
                type="text",
                text=f"✅ Task updated successfully!\n\n"
                     f"**Subject:** {task.get('subject')}\n"
                     f"**ID:** {task.get('id')}\n"
            )]
            
        except Exception as e:
            logger.error(f"Error in update_task: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error updating task: {str(e)}"
            )]
    
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
            
            # Delete task via PM handler
            pm_handler.delete_task(task_id)
            
            return [TextContent(
                type="text",
                text=f"✅ Task {task_id} deleted successfully!"
            )]
            
        except Exception as e:
            logger.error(f"Error in delete_task: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error deleting task: {str(e)}"
            )]
    
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
            
            # Assign task via update
            task = pm_handler.update_task(task_id, assignee_id=assignee_id)
            
            return [TextContent(
                type="text",
                text=f"✅ Task assigned successfully!\n\n"
                     f"**Task:** {task.get('subject')}\n"
                     f"**Assignee:** {task.get('assignee_name')}\n"
            )]
            
        except Exception as e:
            logger.error(f"Error in assign_task: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error assigning task: {str(e)}"
            )]
    
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
            
            # Update task status
            task = pm_handler.update_task(task_id, status=status)
            
            return [TextContent(
                type="text",
                text=f"✅ Task status updated!\n\n"
                     f"**Task:** {task.get('subject')}\n"
                     f"**New Status:** {task.get('status')}\n"
            )]
            
        except Exception as e:
            logger.error(f"Error in update_task_status: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error updating task status: {str(e)}"
            )]
    
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
            
            # Search tasks
            tasks = pm_handler.search_tasks(
                query=query,
                project_id=project_id,
                status=status
            )
            
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
    
    tool_count += 1
    
    logger.info(f"Registered {tool_count} task tools")
    return tool_count

