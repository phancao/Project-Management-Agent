"""
Project Tools Registration (V2)

Registers all refactored project tools with MCP server.
Fully independent - no dependency on backend PM Handler.
"""

import logging
from typing import Any

from mcp.server import Server
from mcp.types import Tool

from ...core.tool_context import ToolContext
from .list_projects import ListProjectsTool
from .get_project import GetProjectTool

logger = logging.getLogger(__name__)


def register_project_tools_v2(
    server: Server,
    context: ToolContext,
    tool_names: list[str] | None = None,
    tool_functions: dict[str, Any] | None = None
) -> int:
    """
    Register refactored project tools (V2) with MCP server.
    
    Fully independent implementation using ProviderManager directly.
    No dependency on backend PM Handler.
    
    Args:
        server: MCP server instance
        context: Tool context with access to managers
        tool_names: Optional list to track tool names
        tool_functions: Optional dict to track tool functions
    
    Returns:
        Number of tools registered
    """
    tool_count = 0
    
    # List of tool classes to register
    tool_classes = [
        ListProjectsTool,
        GetProjectTool,
        # TODO: Add more tools as they are refactored
        # CreateProjectTool,
        # UpdateProjectTool,
        # DeleteProjectTool,
        # SearchProjectsTool,
    ]
    
    for tool_class in tool_classes:
        # Create tool instance
        tool_instance = tool_class(context)
        
        # Get tool metadata from decorator
        tool_name = getattr(tool_class, "_mcp_name", tool_class.__name__)
        tool_description = getattr(tool_class, "_mcp_description", "")
        tool_input_schema = getattr(tool_class, "_mcp_input_schema", {
            "type": "object",
            "properties": {},
            "additionalProperties": True
        })
        
        # Register tool with MCP server
        @server.call_tool()
        async def tool_handler(name: str = tool_name, arguments: dict[str, Any] = None):
            """Tool handler wrapper."""
            return await tool_instance(arguments or {})
        
        # Track tool name and function
        if tool_names is not None:
            tool_names.append(tool_name)
        
        if tool_functions is not None:
            tool_functions[tool_name] = tool_handler
        
        # Add tool to server's tool cache
        if hasattr(server, '_tool_cache'):
            server._tool_cache[tool_name] = Tool(
                name=tool_name,
                description=tool_description,
                inputSchema=tool_input_schema
            )
        
        tool_count += 1
        logger.info(f"[Projects V2] Registered tool: {tool_name}")
    
    logger.info(f"[Projects V2] Registered {tool_count} project tools (fully independent)")
    
    return tool_count

