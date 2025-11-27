"""Update Task Tool"""
from typing import Any
from ..base import WriteTool
from ..decorators import mcp_tool, require_task

@mcp_tool(
    name="update_task",
    description="Update an existing task.",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "Task ID"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "status": {"type": "string"},
            "priority": {"type": "string"}
        },
        "required": ["task_id"]
    }
)
class UpdateTaskTool(WriteTool):
    @require_task
    async def execute(self, task_id: str, **kwargs) -> dict[str, Any]:
        provider = await self._get_first_provider()
        return await provider.update_task(task_id, **kwargs)
    
    async def _get_first_provider(self):
        providers = self.context.provider_manager.get_active_providers()
        if not providers:
            raise ValueError("No active providers")
        return self.context.provider_manager.create_provider_instance(providers[0])

