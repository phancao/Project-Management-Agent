"""
User Management Tools

MCP tools for user operations across all PM providers.
"""

import logging
from typing import Any

from mcp.server import Server
from mcp.types import TextContent

from src.server.pm_handler import PMHandler
from ..config import PMServerConfig

logger = logging.getLogger(__name__)


def register_user_tools(
    server: Server,
    pm_handler: PMHandler,
    config: PMServerConfig
) -> int:
    """
    Register user-related MCP tools.
    
    Args:
        server: MCP server instance
        pm_handler: PM handler for multi-provider operations
        config: Server configuration
    
    Returns:
        Number of tools registered
    """
    tool_count = 0
    
    # Tool 1: list_users
    @server.call_tool()
    async def list_users(arguments: dict[str, Any]) -> list[TextContent]:
        """
        List users in a project or provider.
        
        Args:
            project_id (optional): Filter by project
            provider_id (optional): Filter by provider
        
        Returns:
            List of users
        """
        try:
            project_id = arguments.get("project_id")
            provider_id = arguments.get("provider_id")
            
            logger.info(
                f"list_users called: project_id={project_id}, provider_id={provider_id}"
            )
            
            # Get users from PM handler
            users = pm_handler.list_users(
                project_id=project_id,
                provider_id=provider_id
            )
            
            if not users:
                return [TextContent(
                    type="text",
                    text="No users found."
                )]
            
            # Format output
            output_lines = [f"Found {len(users)} users:\n\n"]
            for i, user in enumerate(users, 1):
                output_lines.append(
                    f"{i}. **{user.get('name')}** (ID: {user.get('id')})\n"
                    f"   Email: {user.get('email', 'N/A')}\n"
                )
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in list_users: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error listing users: {str(e)}"
            )]
    
    tool_count += 1
    
    # Tool 2: get_current_user
    @server.call_tool()
    async def get_current_user(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Get information about the current authenticated user.
        
        Args:
            provider_id (optional): Provider to get user from
        
        Returns:
            Current user information
        """
        try:
            provider_id = arguments.get("provider_id")
            
            logger.info(f"get_current_user called: provider_id={provider_id}")
            
            # Get current user from PM handler
            user = pm_handler.get_current_user(provider_id=provider_id)
            
            if not user:
                return [TextContent(
                    type="text",
                    text="Could not retrieve current user information."
                )]
            
            # Format output
            output_lines = [
                f"# Current User\n\n",
                f"**Name:** {user.get('name')}\n",
                f"**ID:** {user.get('id')}\n",
                f"**Email:** {user.get('email', 'N/A')}\n",
                f"**Provider:** {user.get('provider_type', 'N/A')}\n",
            ]
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in get_current_user: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error getting current user: {str(e)}"
            )]
    
    tool_count += 1
    
    # TODO: Add more user tools:
    # - get_user
    # - search_users
    # - get_user_workload
    
    logger.info(f"Registered {tool_count} user tools")
    return tool_count

