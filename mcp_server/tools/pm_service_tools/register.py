"""
Register PM Service Tools

Registers user tools that use PM Service client.
"""

import logging
from typing import Any
from mcp.server import Server
from mcp.types import Tool

from .users import ListUsersTool, GetUserTool

logger = logging.getLogger(__name__)


def register_pm_service_user_tools(
    server: Server,
    context: any,
    tool_names: list[str] | None = None,
    tool_functions: dict[str, Any] | None = None
) -> int:
    """
    Register PM Service user tools.
    
    Args:
        server: MCP server instance
        context: ToolContext instance
        tool_names: Optional list to track tool names
        tool_functions: Optional dict to store tool functions
    
    Returns:
        Number of tools registered
    """
    tool_count = 0
    
    tool_classes = [
        ListUsersTool,
        GetUserTool,
    ]
    
    for tool_class in tool_classes:
        tool_instance = tool_class(context)
        tool_name = getattr(tool_class, "_mcp_name", tool_class.__name__)
        tool_description = getattr(tool_class, "_mcp_description", "")
        tool_input_schema = getattr(tool_class, "_mcp_input_schema", {"type": "object", "properties": {}, "additionalProperties": True})
        
        # Create a new scope to capture tool_instance correctly
        def create_handler(instance):
            @server.call_tool()
            async def tool_handler(name: str = tool_name, arguments: dict[str, Any] = None):
                from mcp.types import TextContent
                import json
                
                try:
                    # Call execute directly with unpacked arguments (PMServiceTool pattern)
                    if arguments:
                        result = await instance.execute(**arguments)
                    else:
                        result = await instance.execute()
                    # Format as TextContent for MCP response
                    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
                except PermissionError as e:
                    # Format permission errors clearly for the agent
                    error_result = {
                        "error": "PERMISSION_DENIED",
                        "message": str(e),
                        "type": "PermissionError",
                        "users": [],
                        "total": 0,
                        "returned": 0
                    }
                    logger.error(f"[{tool_name}] Permission denied: {e}")
                    return [TextContent(type="text", text=json.dumps(error_result, indent=2, default=str))]
                except Exception as e:
                    # Check if error message contains permission-related keywords
                    error_msg = str(e)
                    if "403" in error_msg or "Forbidden" in error_msg or "permission" in error_msg.lower():
                        error_result = {
                            "error": "PERMISSION_DENIED",
                            "message": f"Permission denied: {error_msg}",
                            "type": "PermissionError",
                            "users": [],
                            "total": 0,
                            "returned": 0
                        }
                        logger.error(f"[{tool_name}] Permission denied: {error_msg}")
                        return [TextContent(type="text", text=json.dumps(error_result, indent=2, default=str))]
                    # For other errors, raise them normally
                    raise
            return tool_handler
        
        handler = create_handler(tool_instance)
        
        if tool_names is not None:
            tool_names.append(tool_name)
        if tool_functions is not None:
            tool_functions[tool_name] = handler
        if hasattr(server, '_tool_cache'):
            server._tool_cache[tool_name] = Tool(name=tool_name, description=tool_description, inputSchema=tool_input_schema)
        
        tool_count += 1
        logger.info(f"[PM Service Tools] Registered tool: {tool_name}")
    
    logger.info(f"[PM Service Tools] Registered {tool_count} user tools")
    return tool_count

