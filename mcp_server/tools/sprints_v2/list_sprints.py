"""List Sprints Tool"""
from typing import Any
from ..base import ReadTool
from ..decorators import mcp_tool

@mcp_tool(
    name="list_sprints",
    description="List sprints from a project.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project ID (format: provider_id:project_key)"},
            "status": {"type": "string", "description": "Optional status filter (active, planned, closed)"}
        },
        "required": ["project_id"]
    }
)
class ListSprintsTool(ReadTool):
    async def execute(self, project_id: str, status: str = None, **kwargs) -> dict[str, Any]:
        # Use the PM handler to list sprints across all providers
        sprints = await self.context.pm_handler.list_all_sprints(project_id=project_id, status=status)
        return {"sprints": sprints, "total": len(sprints)}

