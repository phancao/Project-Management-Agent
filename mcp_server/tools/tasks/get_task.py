"""Get Task Tool"""
from typing import Any
from ..base import ReadTool
from ..decorators import mcp_tool, require_task

@mcp_tool(
    name="get_task",
    description="Get detailed information about a specific task.",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "Task ID"},
            "project_id": {"type": "string", "description": "Project ID (optional)"}
        },
        "required": ["task_id"]
    }
)
class GetTaskTool(ReadTool):
    @require_task
    async def execute(self, task_id: str, project_id: str | None = None) -> dict[str, Any]:
        provider_id, actual_project_id = self._parse_project_id(project_id) if project_id else (None, None)
        provider = await self.context.provider_manager.get_provider(provider_id) if provider_id else (await self._get_first_provider())
        return await provider.get_task(task_id)
    
    async def _get_first_provider(self):
        providers = self.context.provider_manager.get_active_providers()
        if not providers:
            raise ValueError("No active providers")
        return self.context.provider_manager.create_provider_instance(providers[0])
    
    def _parse_project_id(self, project_id: str) -> tuple[str, str]:
        return project_id.split(":", 1) if ":" in project_id else (str(self.context.provider_manager.get_active_providers()[0].id), project_id)

