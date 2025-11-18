"""
Sprint Management Tools

MCP tools for sprint operations across all PM providers.
"""

import logging
from typing import Any

from mcp.server import Server
from mcp.types import TextContent

from src.server.pm_handler import PMHandler
from ..config import PMServerConfig

logger = logging.getLogger(__name__)


def register_sprint_tools(
    server: Server,
    pm_handler: PMHandler,
    config: PMServerConfig
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
            
            # Get sprints from PM handler
            sprints = pm_handler.list_sprints(project_id=project_id, status=status)
            
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
            
            # Get sprint from PM handler
            sprint = pm_handler.get_sprint(sprint_id)
            
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
                f"**Goal:** {sprint.get('goal', 'N/A')}\n",
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
    
    tool_count += 1
    
    # TODO: Add more sprint tools:
    # - create_sprint
    # - update_sprint
    # - delete_sprint
    # - start_sprint
    # - complete_sprint
    # - add_task_to_sprint
    # - remove_task_from_sprint
    # - sprint_planning
    
    logger.info(f"Registered {tool_count} sprint tools")
    return tool_count

