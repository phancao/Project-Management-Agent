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
    
    # Tool 3: get_user
    @server.call_tool()
    async def get_user(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Get detailed information about a user.
        
        Args:
            user_id (required): User ID
            provider_id (optional): Provider to get user from
        
        Returns:
            User information
        """
        try:
            user_id = arguments.get("user_id")
            if not user_id:
                return [TextContent(
                    type="text",
                    text="Error: user_id is required"
                )]
            
            provider_id = arguments.get("provider_id")
            
            logger.info(
                f"get_user called: user_id={user_id}, provider_id={provider_id}"
            )
            
            # Get user from PM handler
            user = pm_handler.get_user(user_id, provider_id=provider_id)
            
            if not user:
                return [TextContent(
                    type="text",
                    text=f"User with ID {user_id} not found."
                )]
            
            # Format output
            output_lines = [
                f"# User: {user.get('name')}\n\n",
                f"**ID:** {user.get('id')}\n",
                f"**Email:** {user.get('email', 'N/A')}\n",
                f"**Provider:** {user.get('provider_type', 'N/A')}\n",
            ]
            
            if "role" in user:
                output_lines.append(f"**Role:** {user['role']}\n")
            
            if "status" in user:
                output_lines.append(f"**Status:** {user['status']}\n")
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in get_user: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error getting user: {str(e)}"
            )]
    
    tool_count += 1
    
    # Tool 4: search_users
    @server.call_tool()
    async def search_users(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Search users by name or email.
        
        Args:
            query (required): Search query
            project_id (optional): Filter by project
            provider_id (optional): Filter by provider
            limit (optional): Maximum results
        
        Returns:
            List of matching users
        """
        try:
            query = arguments.get("query")
            if not query:
                return [TextContent(
                    type="text",
                    text="Error: query is required"
                )]
            
            project_id = arguments.get("project_id")
            provider_id = arguments.get("provider_id")
            limit = arguments.get("limit", 10)
            
            logger.info(
                f"search_users called: query={query}, project_id={project_id}"
            )
            
            # Get users and filter
            users = pm_handler.list_users(
                project_id=project_id,
                provider_id=provider_id
            )
            
            # Filter by query
            query_lower = query.lower()
            matching = [
                u for u in users
                if query_lower in u.get("name", "").lower()
                or query_lower in u.get("email", "").lower()
            ][:int(limit)]
            
            if not matching:
                return [TextContent(
                    type="text",
                    text=f"No users found matching '{query}'"
                )]
            
            output_lines = [f"Found {len(matching)} users matching '{query}':\n\n"]
            for i, user in enumerate(matching, 1):
                output_lines.append(
                    f"{i}. **{user.get('name')}** (ID: {user.get('id')})\n"
                    f"   Email: {user.get('email', 'N/A')}\n"
                )
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in search_users: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error searching users: {str(e)}"
            )]
    
    tool_count += 1
    
    # Tool 5: get_user_workload
    @server.call_tool()
    async def get_user_workload(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Get a user's task workload and capacity.
        
        Args:
            user_id (required): User ID
            provider_id (optional): Provider to check
        
        Returns:
            User workload information
        """
        try:
            user_id = arguments.get("user_id")
            if not user_id:
                return [TextContent(
                    type="text",
                    text="Error: user_id is required"
                )]
            
            provider_id = arguments.get("provider_id")
            
            logger.info(
                f"get_user_workload called: user_id={user_id}, provider_id={provider_id}"
            )
            
            # Get user workload
            workload = pm_handler.get_user_workload(user_id, provider_id=provider_id)
            
            if not workload:
                return [TextContent(
                    type="text",
                    text=f"Could not retrieve workload for user {user_id}."
                )]
            
            # Format output
            output_lines = [
                f"# Workload: {workload.get('user_name')}\n\n",
                f"**Total Tasks:** {workload.get('total_tasks', 0)}\n",
                f"**Open Tasks:** {workload.get('open_tasks', 0)}\n",
                f"**In Progress:** {workload.get('in_progress_tasks', 0)}\n",
                f"**Completed:** {workload.get('completed_tasks', 0)}\n",
                f"**Overdue:** {workload.get('overdue_tasks', 0)}\n",
            ]
            
            if "capacity_percentage" in workload:
                output_lines.append(
                    f"**Capacity:** {workload['capacity_percentage']}%\n"
                )
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in get_user_workload: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error getting user workload: {str(e)}"
            )]
    
    tool_count += 1
    
    logger.info(f"Registered {tool_count} user tools")
    return tool_count

