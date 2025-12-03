"""
User Management Tools

MCP tools for user operations across all PM providers.
"""

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.types import TextContent

logger = logging.getLogger(__name__)


def register_user_tools(
    server: Server,
    context: any,  # ToolContext instance
    tool_names: list[str] | None = None,
    tool_functions: dict[str, Any] | None = None
) -> int:
    """
    Register user-related MCP tools.
    
    Args:
        server: MCP server instance
        context: ToolContext instance
        tool_names: Optional list to track tool names
        tool_functions: Optional dict to store tool functions
    
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
            limit (optional): Maximum number of users to return
        
        Returns:
            List of users
        """
        try:
            project_id = arguments.get("project_id")
            provider_id = arguments.get("provider_id")
            limit = arguments.get("limit", 100)
            
            logger.info(
                f"list_users called: project_id={project_id}, provider_id={provider_id}, limit={limit}"
            )
            
            # Use PM Service to list users
            if context and hasattr(context, 'pm_service'):
                result = await context.pm_service.list_users(
                    project_id=project_id,
                    limit=limit
                )
                
                users = result.get("items", [])
                total = result.get("total", 0)
                
                logger.info(f"list_users returned {len(users)} users (total: {total})")
                
                # Format as JSON for the agent
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "users": users,
                        "total": total,
                        "returned": len(users)
                    }, ensure_ascii=False, indent=2)
                )]
            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "PM Service not available in context",
                        "users": [],
                        "total": 0,
                        "returned": 0
                    }, ensure_ascii=False)
                )]
            
        except Exception as e:
            logger.error(f"Error in list_users: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Error listing users: {str(e)}",
                    "users": [],
                    "total": 0,
                    "returned": 0
                }, ensure_ascii=False)
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("list_users")
    
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
            
            # Current user retrieval is not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Current user retrieval is not yet implemented. "
                     f"Please use the PM provider API endpoints directly."
            )]
            
        except Exception as e:
            logger.error(f"Error in get_current_user: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error getting current user: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("get_current_user")
    
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
            
            # User retrieval is not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"User retrieval is not yet implemented. "
                     f"Please use the PM provider API endpoints directly to get user information."
            )]
            
        except Exception as e:
            logger.error(f"Error in get_user: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error getting user: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("get_user")
    
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
            
            # User listing is not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"User search is not yet implemented. "
                     f"Please use the PM provider API endpoints directly to search users."
            )]
            
        except Exception as e:
            logger.error(f"Error in search_users: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error searching users: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("search_users")
    
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
            
            # User workload is not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"User workload is not yet implemented. "
                     f"Please use the PM provider API endpoints directly to get user workload."
            )]
            
        except Exception as e:
            logger.error(f"Error in get_user_workload: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error getting user workload: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("get_user_workload")
    
    logger.info(f"Registered {tool_count} user tools")
    return tool_count

