"""Task Tools Registration (V2) - Fully Independent"""
import logging
from typing import Any
from mcp.server import Server
from mcp.types import Tool
from ...core.tool_context import ToolContext
from .list_tasks import ListTasksTool
from .list_my_tasks import ListMyTasksTool
from .list_tasks_by_assignee import ListTasksByAssigneeTool
from .list_unassigned_tasks import ListUnassignedTasksTool
from .list_tasks_in_sprint import ListTasksInSprintTool
from .get_task import GetTaskTool
from .create_task import CreateTaskTool
from .update_task import UpdateTaskTool
from .delete_task import DeleteTaskTool
from .assign_task import AssignTaskTool
from .update_task_status import UpdateTaskStatusTool
from .search_tasks import SearchTasksTool

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
        ListMyTasksTool,
        ListTasksByAssigneeTool,
        ListUnassignedTasksTool,
        ListTasksInSprintTool,
        GetTaskTool,
        CreateTaskTool,
        UpdateTaskTool,
        DeleteTaskTool,
        AssignTaskTool,
        UpdateTaskStatusTool,
        SearchTasksTool,
    ]
    
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
        logger.info(f"[Tasks V2] Registered tool: {tool_name}")
    
    logger.info(f"[Tasks V2] Registered {tool_count} task tools (fully independent)")
    return tool_count
