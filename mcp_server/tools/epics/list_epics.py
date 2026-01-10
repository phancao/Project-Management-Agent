"""List Epics Tool"""
from typing import Any
from ..base import ReadTool
from ..decorators import mcp_tool

@mcp_tool(
    name="list_epics",
    description="List epics from a project.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project ID"}
        },
        "required": ["project_id"]
    }
)
class ListEpicsTool(ReadTool):
    async def execute(self, project_id: str, **kwargs) -> dict[str, Any]:
        provider_id, actual_project_id = self._parse_project_id(project_id)
        provider = await self.context.provider_manager.get_provider(provider_id)
        epics = await provider.list_epics(actual_project_id)
        return {"epics": epics, "total": len(epics)}
    
    def _parse_project_id(self, project_id: str) -> tuple[str, str]:
        return project_id.split(":", 1) if ":" in project_id else (str(self.context.provider_manager.get_active_providers()[0].id), project_id)

