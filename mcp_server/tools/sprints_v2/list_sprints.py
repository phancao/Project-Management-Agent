"""List Sprints Tool"""
from typing import Any
from ..base import ReadTool
from ..decorators import mcp_tool

@mcp_tool(
    name="list_sprints",
    description="List sprints from a project or provider. Supports filtering by status (active/planned/closed).",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project ID (format: provider_id:project_key)"},
            "status": {"type": "string", "description": "Optional status filter (active, planned, closed)"},
            "provider_id": {"type": "string", "description": "Optional provider ID to filter by specific provider"}
        }
    }
)
class ListSprintsTool(ReadTool):
    async def execute(
        self, 
        project_id: str | None = None, 
        status: str | None = None, 
        provider_id: str | None = None,
        **kwargs
    ) -> dict[str, Any]:
        # Use the PM Service client to list sprints
        result = await self.context.pm_service.list_sprints(
            project_id=project_id,
            state=status,
            provider_id=provider_id
        )
        return {
            "sprints": result.get("items", []),
            "total": result.get("total", 0)
        }

