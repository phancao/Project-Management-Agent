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
    
    # TODO: Add more epic tools:
    # - create_epic
    # - update_epic
    # - delete_epic
    # - link_task_to_epic
    # - unlink_task_from_epic
    # - get_epic_progress
    
    logger.info(f"Registered {tool_count} epic tools")
    return tool_count

