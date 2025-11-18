"""
Epic Management Tools

MCP tools for epic operations across all PM providers.
"""

import logging
from typing import Any

from mcp.server import Server
from mcp.types import TextContent

from src.server.pm_handler import PMHandler
from ..config import PMServerConfig

logger = logging.getLogger(__name__)


def register_epic_tools(
    server: Server,
    pm_handler: PMHandler,
    config: PMServerConfig
) -> int:
    """
    Register epic-related MCP tools.
    
    Args:
        server: MCP server instance
        pm_handler: PM handler for multi-provider operations
        config: Server configuration
    
    Returns:
        Number of tools registered
    """
    tool_count = 0
    
    # Tool 1: list_epics
    @server.call_tool()
    async def list_epics(arguments: dict[str, Any]) -> list[TextContent]:
        """
        List epics in a project.
        
        Args:
            project_id (required): Project ID
        
        Returns:
            List of epics
        """
        try:
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required"
                )]
            
            logger.info(f"list_epics called: project_id={project_id}")
            
            # Get epics from PM handler
            epics = pm_handler.list_epics(project_id=project_id)
            
            if not epics:
                return [TextContent(
                    type="text",
                    text=f"No epics found in project {project_id}."
                )]
            
            # Format output
            output_lines = [f"Found {len(epics)} epics:\n\n"]
            for i, epic in enumerate(epics, 1):
                output_lines.append(
                    f"{i}. **{epic.get('name')}** (ID: {epic.get('id')})\n"
                    f"   Status: {epic.get('status', 'N/A')}\n"
                )
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in list_epics: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error listing epics: {str(e)}"
            )]
    
    tool_count += 1
    
    # Tool 2: get_epic
    @server.call_tool()
    async def get_epic(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Get detailed information about an epic.
        
        Args:
            epic_id (required): Epic ID
        
        Returns:
            Detailed epic information
        """
        try:
            epic_id = arguments.get("epic_id")
            if not epic_id:
                return [TextContent(
                    type="text",
                    text="Error: epic_id is required"
                )]
            
            logger.info(f"get_epic called: epic_id={epic_id}")
            
            # Get epic from PM handler
            epic = pm_handler.get_epic(epic_id)
            
            if not epic:
                return [TextContent(
                    type="text",
                    text=f"Epic with ID {epic_id} not found."
                )]
            
            # Format output
            output_lines = [
                f"# Epic: {epic.get('name')}\n\n",
                f"**ID:** {epic.get('id')}\n",
                f"**Status:** {epic.get('status', 'N/A')}\n",
                f"**Description:** {epic.get('description', 'N/A')}\n",
            ]
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in get_epic: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error getting epic: {str(e)}"
            )]
    
    tool_count += 1
    
    # Tool 3: create_epic
    @server.call_tool()
    async def create_epic(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Create a new epic.
        
        Args:
            project_id (required): Project ID
            name (required): Epic name
            description (optional): Epic description
        
        Returns:
            Created epic information
        """
        try:
            project_id = arguments.get("project_id")
            name = arguments.get("name")
            
            if not project_id or not name:
                return [TextContent(
                    type="text",
                    text="Error: project_id and name are required"
                )]
            
            description = arguments.get("description")
            
            logger.info(
                f"create_epic called: project_id={project_id}, name={name}"
            )
            
            # Create epic via PM handler
            epic = pm_handler.create_epic(
                project_id=project_id,
                name=name,
                description=description
            )
            
            return [TextContent(
                type="text",
                text=f"✅ Epic created successfully!\n\n"
                     f"**Name:** {epic.get('name')}\n"
                     f"**ID:** {epic.get('id')}\n"
            )]
            
        except Exception as e:
            logger.error(f"Error in create_epic: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error creating epic: {str(e)}"
            )]
    
    tool_count += 1
    
    # Tool 4: update_epic
    @server.call_tool()
    async def update_epic(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Update an existing epic.
        
        Args:
            epic_id (required): Epic ID
            name (optional): New epic name
            description (optional): New description
            status (optional): New status
        
        Returns:
            Updated epic information
        """
        try:
            epic_id = arguments.get("epic_id")
            if not epic_id:
                return [TextContent(
                    type="text",
                    text="Error: epic_id is required"
                )]
            
            updates = {
                k: v for k, v in arguments.items()
                if k != "epic_id" and v is not None
            }
            
            if not updates:
                return [TextContent(
                    type="text",
                    text="Error: At least one field to update is required"
                )]
            
            logger.info(
                f"update_epic called: epic_id={epic_id}, updates={updates}"
            )
            
            # Update epic via PM handler
            epic = pm_handler.update_epic(epic_id, **updates)
            
            return [TextContent(
                type="text",
                text=f"✅ Epic updated successfully!\n\n"
                     f"**Name:** {epic.get('name')}\n"
                     f"**ID:** {epic.get('id')}\n"
            )]
            
        except Exception as e:
            logger.error(f"Error in update_epic: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error updating epic: {str(e)}"
            )]
    
    tool_count += 1
    
    # Tool 5: delete_epic
    @server.call_tool()
    async def delete_epic(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Delete an epic.
        
        Args:
            epic_id (required): Epic ID
        
        Returns:
            Confirmation message
        """
        try:
            epic_id = arguments.get("epic_id")
            if not epic_id:
                return [TextContent(
                    type="text",
                    text="Error: epic_id is required"
                )]
            
            logger.info(f"delete_epic called: epic_id={epic_id}")
            
            # Delete epic via PM handler
            pm_handler.delete_epic(epic_id)
            
            return [TextContent(
                type="text",
                text=f"✅ Epic {epic_id} deleted successfully!"
            )]
            
        except Exception as e:
            logger.error(f"Error in delete_epic: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error deleting epic: {str(e)}"
            )]
    
    tool_count += 1
    
    # Tool 6: link_task_to_epic
    @server.call_tool()
    async def link_task_to_epic(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Link a task to an epic.
        
        Args:
            task_id (required): Task ID
            epic_id (required): Epic ID
        
        Returns:
            Confirmation message
        """
        try:
            task_id = arguments.get("task_id")
            epic_id = arguments.get("epic_id")
            
            if not task_id or not epic_id:
                return [TextContent(
                    type="text",
                    text="Error: task_id and epic_id are required"
                )]
            
            logger.info(
                f"link_task_to_epic called: task_id={task_id}, epic_id={epic_id}"
            )
            
            # Link task to epic by updating task
            task = pm_handler.update_task(task_id, epic_id=epic_id)
            
            return [TextContent(
                type="text",
                text=f"✅ Task linked to epic!\n\n"
                     f"**Task:** {task.get('subject')}\n"
                     f"**Epic ID:** {epic_id}\n"
            )]
            
        except Exception as e:
            logger.error(f"Error in link_task_to_epic: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error linking task to epic: {str(e)}"
            )]
    
    tool_count += 1
    
    # Tool 7: unlink_task_from_epic
    @server.call_tool()
    async def unlink_task_from_epic(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Unlink a task from an epic.
        
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
            
            logger.info(f"unlink_task_from_epic called: task_id={task_id}")
            
            # Unlink task from epic by setting epic_id to None
            task = pm_handler.update_task(task_id, epic_id=None)
            
            return [TextContent(
                type="text",
                text=f"✅ Task unlinked from epic!\n\n"
                     f"**Task:** {task.get('subject')}\n"
            )]
            
        except Exception as e:
            logger.error(f"Error in unlink_task_from_epic: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error unlinking task from epic: {str(e)}"
            )]
    
    tool_count += 1
    
    # Tool 8: get_epic_progress
    @server.call_tool()
    async def get_epic_progress(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Get epic completion progress.
        
        Args:
            epic_id (required): Epic ID
        
        Returns:
            Epic progress information
        """
        try:
            epic_id = arguments.get("epic_id")
            if not epic_id:
                return [TextContent(
                    type="text",
                    text="Error: epic_id is required"
                )]
            
            logger.info(f"get_epic_progress called: epic_id={epic_id}")
            
            # Get epic progress
            progress = pm_handler.get_epic_progress(epic_id)
            
            if not progress:
                return [TextContent(
                    type="text",
                    text=f"Could not retrieve progress for epic {epic_id}."
                )]
            
            # Format output
            output_lines = [
                f"# Epic Progress: {progress.get('name')}\n\n",
                f"**Total Tasks:** {progress.get('total_tasks', 0)}\n",
                f"**Completed Tasks:** {progress.get('completed_tasks', 0)}\n",
                f"**In Progress:** {progress.get('in_progress_tasks', 0)}\n",
                f"**Pending:** {progress.get('pending_tasks', 0)}\n",
                f"**Completion:** {progress.get('completion_percentage', 0)}%\n",
            ]
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in get_epic_progress: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error getting epic progress: {str(e)}"
            )]
    
    tool_count += 1
    
    logger.info(f"Registered {tool_count} epic tools")
    return tool_count

