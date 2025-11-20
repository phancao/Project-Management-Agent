"""
Sprint Management Tools

MCP tools for sprint operations across all PM providers.
"""

import logging
from typing import Any

from mcp.server import Server
from mcp.types import TextContent

from ..pm_handler import MCPPMHandler
from ..config import PMServerConfig

logger = logging.getLogger(__name__)


def register_sprint_tools(
    server: Server,
    pm_handler: MCPPMHandler,
    config: PMServerConfig,
    tool_names: list[str] | None = None
) -> int:
    """
    Register sprint-related MCP tools.
    
    Args:
        server: MCP server instance
        pm_handler: PM handler for multi-provider operations
        config: Server configuration
    
    Returns:
        Number of tools registered
    """
    tool_count = 0
    
    # Tool 1: list_sprints
    @server.call_tool()
    async def list_sprints(arguments: dict[str, Any]) -> list[TextContent]:
        """
        List sprints in a project.
        
        Args:
            project_id (required): Project ID
            status (optional): Filter by status (active, planned, closed)
        
        Returns:
            List of sprints
        """
        try:
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required"
                )]
            
            status = arguments.get("status")
            
            logger.info(
                f"list_sprints called: project_id={project_id}, status={status}"
            )
            
            # Get sprints from PM handler using list_project_sprints
            sprints = await pm_handler.list_project_sprints(project_id, state=status)
            
            if not sprints:
                return [TextContent(
                    type="text",
                    text=f"No sprints found in project {project_id}."
                )]
            
            # Format output
            output_lines = [f"Found {len(sprints)} sprints:\n\n"]
            for i, sprint in enumerate(sprints, 1):
                output_lines.append(
                    f"{i}. **{sprint.get('name')}** (ID: {sprint.get('id')})\n"
                    f"   Status: {sprint.get('status', 'N/A')} | "
                    f"Duration: {sprint.get('start_date', 'N/A')} - {sprint.get('end_date', 'N/A')}\n"
                )
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in list_sprints: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error listing sprints: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("list_sprints")
    tool_count += 1
    
    # Tool 2: get_sprint
    @server.call_tool()
    async def get_sprint(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Get detailed information about a sprint.
        
        Args:
            sprint_id (required): Sprint ID
        
        Returns:
            Detailed sprint information
        """
        try:
            sprint_id = arguments.get("sprint_id")
            if not sprint_id:
                return [TextContent(
                    type="text",
                    text="Error: sprint_id is required"
                )]
            
            logger.info(f"get_sprint called: sprint_id={sprint_id}")
            
            # Get sprint by searching all projects
            # Extract project_id from sprint_id if in format "project_id:sprint_id"
            if ":" in sprint_id:
                project_id_part, sprint_id_part = sprint_id.split(":", 1)
                sprints = await pm_handler.list_project_sprints(project_id_part)
                sprint = next((s for s in sprints if str(s.get("id")) == sprint_id_part), None)
            else:
                # Search all projects - need project_id to search
                return [TextContent(
                    type="text",
                    text=f"Sprint ID format should be 'project_id:sprint_id'. "
                         f"Please provide project_id to search for sprint {sprint_id}."
                )]
            
            if not sprint:
                return [TextContent(
                    type="text",
                    text=f"Sprint with ID {sprint_id} not found."
                )]
            
            # Format output
            output_lines = [
                f"# Sprint: {sprint.get('name')}\n\n",
                f"**ID:** {sprint.get('id')}\n",
                f"**Status:** {sprint.get('status', 'N/A')}\n",
                f"**Start Date:** {sprint.get('start_date', 'N/A')}\n",
                f"**End Date:** {sprint.get('end_date', 'N/A')}\n",
            ]
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in get_sprint: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error getting sprint: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("get_sprint")
    tool_count += 1
    
    # Tool 3: create_sprint
    @server.call_tool()
    async def create_sprint(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Create a new sprint.
        
        Args:
            project_id (required): Project ID
            name (required): Sprint name
            start_date (required): Start date (YYYY-MM-DD)
            end_date (required): End date (YYYY-MM-DD)
            goal (optional): Sprint goal
        
        Returns:
            Created sprint information
        """
        try:
            project_id = arguments.get("project_id")
            name = arguments.get("name")
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            
            if not all([project_id, name, start_date, end_date]):
                return [TextContent(
                    type="text",
                    text="Error: project_id, name, start_date, and end_date are required"
                )]
            
            goal = arguments.get("goal")
            
            logger.info(
                f"create_sprint called: project_id={project_id}, name={name}"
            )
            
            # Sprint creation is not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Sprint creation is not yet implemented. "
                     f"Please create sprints directly in your PM provider (JIRA, OpenProject, etc.)."
            )]
            
        except Exception as e:
            logger.error(f"Error in create_sprint: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error creating sprint: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("create_sprint")
    tool_count += 1
    
    # Tool 4: update_sprint
    @server.call_tool()
    async def update_sprint(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Update an existing sprint.
        
        Args:
            sprint_id (required): Sprint ID
            name (optional): New sprint name
            start_date (optional): New start date
            end_date (optional): New end date
            goal (optional): New sprint goal
            status (optional): New status
        
        Returns:
            Updated sprint information
        """
        try:
            sprint_id = arguments.get("sprint_id")
            if not sprint_id:
                return [TextContent(
                    type="text",
                    text="Error: sprint_id is required"
                )]
            
            updates = {
                k: v for k, v in arguments.items()
                if k != "sprint_id" and v is not None
            }
            
            if not updates:
                return [TextContent(
                    type="text",
                    text="Error: At least one field to update is required"
                )]
            
            logger.info(
                f"update_sprint called: sprint_id={sprint_id}, updates={updates}"
            )
            
            # Sprint update is not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Sprint update is not yet implemented. "
                     f"Please update sprints directly in your PM provider (JIRA, OpenProject, etc.)."
            )]
            
        except Exception as e:
            logger.error(f"Error in update_sprint: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error updating sprint: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("update_sprint")
    tool_count += 1
    
    # Tool 5: delete_sprint
    @server.call_tool()
    async def delete_sprint(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Delete a sprint.
        
        Args:
            sprint_id (required): Sprint ID
        
        Returns:
            Confirmation message
        """
        try:
            sprint_id = arguments.get("sprint_id")
            if not sprint_id:
                return [TextContent(
                    type="text",
                    text="Error: sprint_id is required"
                )]
            
            logger.info(f"delete_sprint called: sprint_id={sprint_id}")
            
            # Sprint deletion is not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Sprint deletion is not yet implemented. "
                     f"Please delete sprints directly in your PM provider (JIRA, OpenProject, etc.)."
            )]
            
        except Exception as e:
            logger.error(f"Error in delete_sprint: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error deleting sprint: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("delete_sprint")
    
    # Tool 6: start_sprint
    @server.call_tool()
    async def start_sprint(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Start a sprint (change status to active).
        
        Args:
            sprint_id (required): Sprint ID
        
        Returns:
            Confirmation message
        """
        try:
            sprint_id = arguments.get("sprint_id")
            if not sprint_id:
                return [TextContent(
                    type="text",
                    text="Error: sprint_id is required"
                )]
            
            logger.info(f"start_sprint called: sprint_id={sprint_id}")
            
            # Sprint start is not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Sprint start is not yet implemented. "
                     f"Please start sprints directly in your PM provider (JIRA, OpenProject, etc.)."
            )]
            
        except Exception as e:
            logger.error(f"Error in start_sprint: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error starting sprint: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("start_sprint")
    
    # Tool 7: complete_sprint
    @server.call_tool()
    async def complete_sprint(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Complete a sprint (change status to closed).
        
        Args:
            sprint_id (required): Sprint ID
        
        Returns:
            Confirmation message with sprint summary
        """
        try:
            sprint_id = arguments.get("sprint_id")
            if not sprint_id:
                return [TextContent(
                    type="text",
                    text="Error: sprint_id is required"
                )]
            
            logger.info(f"complete_sprint called: sprint_id={sprint_id}")
            
            # Sprint completion is not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Sprint completion is not yet implemented. "
                     f"Please complete sprints directly in your PM provider (JIRA, OpenProject, etc.)."
            )]
            
        except Exception as e:
            logger.error(f"Error in complete_sprint: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error completing sprint: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("complete_sprint")
    
    # Tool 8: add_task_to_sprint
    @server.call_tool()
    async def add_task_to_sprint(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Add a task to a sprint.
        
        Args:
            task_id (required): Task ID
            sprint_id (required): Sprint ID
        
        Returns:
            Confirmation message
        """
        try:
            task_id = arguments.get("task_id")
            sprint_id = arguments.get("sprint_id")
            
            if not task_id or not sprint_id:
                return [TextContent(
                    type="text",
                    text="Error: task_id and sprint_id are required"
                )]
            
            logger.info(
                f"add_task_to_sprint called: task_id={task_id}, sprint_id={sprint_id}"
            )
            
            # Extract project_id from task_id if in format "project_id:task_id"
            if ":" in task_id:
                project_id_part, task_id_part = task_id.split(":", 1)
                result = await pm_handler.assign_task_to_sprint(project_id_part, task_id_part, sprint_id)
                return [TextContent(
                    type="text",
                    text=f"✅ Task added to sprint!\n\n"
                         f"**Task:** {result.get('subject', task_id)}\n"
                         f"**Sprint ID:** {sprint_id}\n"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Task ID format should be 'project_id:task_id'. Cannot add task {task_id} to sprint."
                )]
            
        except Exception as e:
            logger.error(f"Error in add_task_to_sprint: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error adding task to sprint: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("add_task_to_sprint")
    
    # Tool 9: remove_task_from_sprint
    @server.call_tool()
    async def remove_task_from_sprint(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Remove a task from a sprint.
        
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
            
            logger.info(f"remove_task_from_sprint called: task_id={task_id}")
            
            # Extract project_id from task_id if in format "project_id:task_id"
            if ":" in task_id:
                project_id_part, task_id_part = task_id.split(":", 1)
                result = await pm_handler.move_task_to_backlog(project_id_part, task_id_part)
                return [TextContent(
                    type="text",
                    text=f"✅ Task removed from sprint!\n\n"
                         f"**Task:** {result.get('subject', task_id)}\n"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Task ID format should be 'project_id:task_id'. Cannot remove task {task_id} from sprint."
                )]
            
        except Exception as e:
            logger.error(f"Error in remove_task_from_sprint: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error removing task from sprint: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("remove_task_from_sprint")
    tool_count += 1
    
    # Tool 10: get_sprint_tasks
    @server.call_tool()
    async def get_sprint_tasks(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Get all tasks in a sprint.
        
        Args:
            sprint_id (required): Sprint ID
        
        Returns:
            List of tasks in the sprint
        """
        try:
            sprint_id = arguments.get("sprint_id")
            if not sprint_id:
                return [TextContent(
                    type="text",
                    text="Error: sprint_id is required"
                )]
            
            logger.info(f"get_sprint_tasks called: sprint_id={sprint_id}")
            
            # Get tasks in sprint by listing project tasks and filtering
            # Extract project_id from sprint_id if in format "project_id:sprint_id"
            if ":" in sprint_id:
                project_id_part, sprint_id_part = sprint_id.split(":", 1)
                tasks = await pm_handler.list_project_tasks(project_id_part)
                # Filter by sprint_id
                tasks = [t for t in tasks if str(t.get("sprint_id")) == sprint_id_part]
            else:
                return [TextContent(
                    type="text",
                    text=f"Sprint ID format should be 'project_id:sprint_id'. Cannot get tasks for sprint {sprint_id}."
                )]
            
            if not tasks:
                return [TextContent(
                    type="text",
                    text=f"No tasks found in sprint {sprint_id}."
                )]
            
            # Format output
            output_lines = [f"Found {len(tasks)} tasks in sprint:\n\n"]
            for i, task in enumerate(tasks, 1):
                output_lines.append(
                    f"{i}. **{task.get('subject') or task.get('title', 'N/A')}** (ID: {task.get('id')})\n"
                    f"   Status: {task.get('status', 'N/A')} | "
                    f"Assignee: {task.get('assignee_name', task.get('assigned_to', 'Unassigned'))}\n"
                )
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in get_sprint_tasks: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error getting sprint tasks: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("get_sprint_tasks")
    tool_count += 1
    
    logger.info(f"Registered {tool_count} sprint tools")
    return tool_count

