"""
Analytics Tools Registration

Helper functions to register refactored analytics tools with MCP server.
"""

import logging
from typing import Any

from mcp.server import Server
from mcp.types import Tool

from ...core.tool_context import ToolContext
from . import (
    BurndownChartTool,
    VelocityChartTool,
    SprintReportTool,
    ProjectHealthTool,
)

logger = logging.getLogger(__name__)


def register_analytics_tools_v2(
    server: Server,
    context: ToolContext,
    tool_names: list[str] | None = None,
    tool_functions: dict[str, Any] | None = None
) -> int:
    """
    Register refactored analytics tools with MCP server.
    
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
        BurndownChartTool,
        VelocityChartTool,
        SprintReportTool,
        ProjectHealthTool,
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
        
        # IMPORTANT: Create a new scope to capture tool_instance correctly
        # Without this, all handlers would reference the last tool_instance due to closure
        def create_handler(instance):
            @server.call_tool()
            async def tool_handler(name: str = tool_name, arguments: dict[str, Any] = None):
                """Tool handler wrapper."""
                return await instance(arguments or {})
            return tool_handler
        
        handler = create_handler(tool_instance)
        
        # Track tool name and function
        if tool_names is not None:
            tool_names.append(tool_name)
        
        if tool_functions is not None:
            tool_functions[tool_name] = handler
        
        # Add tool to server's tool cache
        if hasattr(server, '_tool_cache'):
            server._tool_cache[tool_name] = Tool(
                name=tool_name,
                description=tool_description,
                inputSchema=tool_input_schema
            )
        
        tool_count += 1
        logger.info(f"[Analytics V2] Registered tool: {tool_name}")
    
    logger.info(f"[Analytics V2] Registered {tool_count} analytics tools")
    
    return tool_count


