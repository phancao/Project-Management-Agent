# PM Service - Sprints Tools
"""
Sprint tools using PM Service client.
"""

from typing import Any, Optional

from ..pm_service_base import PMServiceReadTool
from ..decorators import mcp_tool


@mcp_tool(
    name="list_sprints",
    description=(
        "List sprints from PM providers. "
        "Supports filtering by project and status."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Filter by project ID (format: provider_id:project_key)"
            },
            "status": {
                "type": "string",
                "description": "Filter by status (active, closed, future)"
            }
        }
    }
)
class ListSprintsTool(PMServiceReadTool):
    """List sprints."""
    
    async def execute(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> dict[str, Any]:
        """List sprints using PM Service."""
        async with self.client as client:
            result = await client.list_sprints(
                project_id=project_id,
                status=status
            )
        
        return {
            "sprints": result.get("items", []),
            "total": result.get("total", 0)
        }


@mcp_tool(
    name="get_sprint",
    description="Get detailed information about a specific sprint.",
    input_schema={
        "type": "object",
        "properties": {
            "sprint_id": {
                "type": "string",
                "description": "Sprint ID (format: provider_id:sprint_id or just numeric ID)"
            }
        },
        "required": ["sprint_id"]
    }
)
class GetSprintTool(PMServiceReadTool):
    """Get sprint details."""
    
    async def execute(self, sprint_id: str) -> dict[str, Any]:
        """Get sprint using PM Service."""
        async with self.client as client:
            return await client.get_sprint(sprint_id)
