"""Create Task Tool"""
from typing import Any
from ..base import WriteTool
from ..decorators import mcp_tool, require_project

@mcp_tool(
    name="create_task",
    description="Create a new task in a project.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project ID"},
            "title": {"type": "string", "description": "Task title"},
            "description": {"type": "string", "description": "Task description"},
            "assignee_id": {"type": "string", "description": "Assignee user ID"},
            "priority": {"type": "string", "description": "Priority"},
            "due_date": {"type": "string", "description": "Due date"}
        },
        "required": ["project_id", "title"]
    }
)
class CreateTaskTool(WriteTool):
    @require_project
    async def execute(self, project_id: str, title: str, **kwargs) -> dict[str, Any]:
        provider_id, actual_project_id = self._parse_project_id(project_id)
        provider = await self.context.provider_manager.get_provider(provider_id)
        return await provider.create_task(project_id=actual_project_id, title=title, **kwargs)
    
    def _parse_project_id(self, project_id: str) -> tuple[str, str]:
        return project_id.split(":", 1) if ":" in project_id else (str(self.context.provider_manager.get_active_providers()[0].id), project_id)

