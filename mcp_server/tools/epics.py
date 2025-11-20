"""
Epic Management Tools

MCP tools for epic operations across all PM providers.
"""

import logging
from typing import Any

from mcp.server import Server
from mcp.types import TextContent

from ..pm_handler import MCPPMHandler
from ..config import PMServerConfig

logger = logging.getLogger(__name__)


def register_epic_tools(
    server: Server,
    pm_handler: MCPPMHandler,
    config: PMServerConfig,
    tool_names: list[str] | None = None
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
            
            # Get epics from PM handler using list_project_epics
            epics = await pm_handler.list_project_epics(project_id)
            
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
    
    if tool_names is not None:
        tool_names.append("list_epics")
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
            
            # Get epic by searching project epics
            # Extract project_id from epic_id if in format "project_id:epic_id"
            if ":" in epic_id:
                project_id_part, epic_id_part = epic_id.split(":", 1)
                epics = await pm_handler.list_project_epics(project_id_part)
                epic = next((e for e in epics if str(e.get("id")) == epic_id_part), None)
            else:
                return [TextContent(
                    type="text",
                    text=f"Epic ID format should be 'project_id:epic_id'. Please provide project_id to search for epic {epic_id}."
                )]
            
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
    
    if tool_names is not None:
        tool_names.append("get_epic")
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
            
            # Create epic via PM handler using create_project_epic
            epic_data = {"name": name, "description": description}
            epic = await pm_handler.create_project_epic(project_id, epic_data)
            
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
    
    if tool_names is not None:
        tool_names.append("create_epic")
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
            
            # Update epic via PM handler using update_project_epic
            # Extract project_id from epic_id if in format "project_id:epic_id"
            if ":" in epic_id:
                project_id_part, epic_id_part = epic_id.split(":", 1)
                epic = await pm_handler.update_project_epic(project_id_part, epic_id_part, updates)
            else:
                return [TextContent(
                    type="text",
                    text=f"Epic ID format should be 'project_id:epic_id'. Cannot update epic {epic_id}."
                )]
            
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
    
    if tool_names is not None:
        tool_names.append("update_epic")
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
            
            # Delete epic via PM handler using delete_project_epic
            # Extract project_id from epic_id if in format "project_id:epic_id"
            if ":" in epic_id:
                project_id_part, epic_id_part = epic_id.split(":", 1)
                await pm_handler.delete_project_epic(project_id_part, epic_id_part)
            else:
                return [TextContent(
                    type="text",
                    text=f"Epic ID format should be 'project_id:epic_id'. Cannot delete epic {epic_id}."
                )]
            
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
    if tool_names is not None:
        tool_names.append("delete_epic")
    
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
            
            # Link task to epic using assign_task_to_epic
            # Extract project_id from task_id if in format "project_id:task_id"
            if ":" in task_id:
                project_id_part, task_id_part = task_id.split(":", 1)
                result = await pm_handler.assign_task_to_epic(project_id_part, task_id_part, epic_id)
                return [TextContent(
                    type="text",
                    text=f"✅ Task linked to epic!\n\n"
                         f"**Task:** {result.get('subject', task_id)}\n"
                         f"**Epic ID:** {epic_id}\n"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Task ID format should be 'project_id:task_id'. Cannot link task {task_id} to epic."
                )]
            
        except Exception as e:
            logger.error(f"Error in link_task_to_epic: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error linking task to epic: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("link_task_to_epic")
    
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
            
            # Unlink task from epic using remove_task_from_epic
            # Extract project_id from task_id if in format "project_id:task_id"
            if ":" in task_id:
                project_id_part, task_id_part = task_id.split(":", 1)
                result = await pm_handler.remove_task_from_epic(project_id_part, task_id_part)
                return [TextContent(
                    type="text",
                    text=f"✅ Task unlinked from epic!\n\n"
                         f"**Task:** {result.get('subject', task_id)}\n"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Task ID format should be 'project_id:task_id'. Cannot unlink task {task_id} from epic."
                )]
            
        except Exception as e:
            logger.error(f"Error in unlink_task_from_epic: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error unlinking task from epic: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("unlink_task_from_epic")
    
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
            
            # Epic progress is not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Epic progress is not yet implemented. "
                     f"Please check epic progress directly in your PM provider (JIRA, OpenProject, etc.)."
            )]
            
        except Exception as e:
            logger.error(f"Error in get_epic_progress: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error getting epic progress: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("get_epic_progress")
    
    logger.info(f"Registered {tool_count} epic tools")
    return tool_count

