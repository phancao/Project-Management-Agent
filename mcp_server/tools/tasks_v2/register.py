"""Task Tools Registration (V2) - Fully Independent"""
import logging
from typing import Any
from mcp.server import Server
from mcp.types import Tool
from ...core.tool_context import ToolContext
from .list_tasks import ListTasksTool
from .get_task import GetTaskTool
from .create_task import CreateTaskTool
from .update_task import UpdateTaskTool

logger = logging.getLogger(__name__)

def register_task_tools_v2(
    server: Server,
    context: ToolContext,
    tool_names: list[str] | None = None,
    tool_functions: dict[str, Any] | None = None
) -> int:
    """Register task tools (V2) - fully independent."""
    tool_count = 0
    
    tool_classes = [
        ListTasksTool,
        GetTaskTool,
        CreateTaskTool,
        UpdateTaskTool,
        # TODO: Add remaining tools as needed
    ]
    
    for tool_class in tool_classes:
        tool_instance = tool_class(context)
        tool_name = getattr(tool_class, "_mcp_name", tool_class.__name__)
        tool_description = getattr(tool_class, "_mcp_description", "")
        tool_input_schema = getattr(tool_class, "_mcp_input_schema", {"type": "object", "properties": {}, "additionalProperties": True})
        
        @server.call_tool()
        async def tool_handler(name: str = tool_name, arguments: dict[str, Any] = None):
            return await tool_instance(arguments or {})
        
        if tool_names is not None:
            tool_names.append(tool_name)
        if tool_functions is not None:
            tool_functions[tool_name] = tool_handler
        if hasattr(server, '_tool_cache'):
            server._tool_cache[tool_name] = Tool(name=tool_name, description=tool_description, inputSchema=tool_input_schema)
        
        tool_count += 1
        logger.info(f"[Tasks V2] Registered tool: {tool_name}")
    
    logger.info(f"[Tasks V2] Registered {tool_count} task tools (fully independent)")
    return tool_count
