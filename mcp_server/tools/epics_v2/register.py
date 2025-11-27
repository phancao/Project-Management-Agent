"""Epic Tools Registration (V2) - Fully Independent"""
import logging
from typing import Any
from mcp.server import Server
from mcp.types import Tool
from ...core.tool_context import ToolContext
from .list_epics import ListEpicsTool
from .get_epic import GetEpicTool

logger = logging.getLogger(__name__)

def register_epic_tools_v2(
    server: Server,
    context: ToolContext,
    tool_names: list[str] | None = None,
    tool_functions: dict[str, Any] | None = None
) -> int:
    """Register epic tools (V2) - fully independent."""
    tool_count = 0
    
    tool_classes = [ListEpicsTool, GetEpicTool]
    
    for tool_class in tool_classes:
        tool_instance = tool_class(context)
        tool_name = getattr(tool_class, "_mcp_name", tool_class.__name__)
        tool_description = getattr(tool_class, "_mcp_description", "")
        tool_input_schema = getattr(tool_class, "_mcp_input_schema", {"type": "object", "properties": {}, "additionalProperties": True})
        
        # IMPORTANT: Create a new scope to capture tool_instance correctly
        # Without this, all handlers would reference the last tool_instance due to closure
        def create_handler(instance):
            @server.call_tool()
            async def tool_handler(name: str = tool_name, arguments: dict[str, Any] = None):
                return await instance(arguments or {})
            return tool_handler
        
        handler = create_handler(tool_instance)
        
        if tool_names is not None:
            tool_names.append(tool_name)
        if tool_functions is not None:
            tool_functions[tool_name] = handler
        if hasattr(server, '_tool_cache'):
            server._tool_cache[tool_name] = Tool(name=tool_name, description=tool_description, inputSchema=tool_input_schema)
        
        tool_count += 1
        logger.info(f"[Epics V2] Registered tool: {tool_name}")
    
    logger.info(f"[Epics V2] Registered {tool_count} epic tools (fully independent)")
    return tool_count
