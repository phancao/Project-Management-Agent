# PM Service - Projects Tools
"""
Project tools using PM Service client.
"""

from typing import Any, Optional

from ..pm_service_base import PMServiceReadTool
from ..decorators import mcp_tool


@mcp_tool(
    name="list_projects",
    description=(
        "List all accessible projects across all PM providers. "
        "Returns project information including name, description, status, and provider details."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "provider_id": {
                "type": "string",
                "description": "Filter projects by provider ID (optional)"
            }
        }
    }
)
class ListProjectsTool(PMServiceReadTool):
    """List all accessible projects."""
    
    async def execute(
        self,
        provider_id: Optional[str] = None
    ) -> dict[str, Any]:
        """List projects using PM Service."""
        async with self.client as client:
            result = await client.list_projects(
                provider_id=provider_id
            )
        
        return {
            "projects": result.get("items", []),
            "total": result.get("total", 0)
        }


@mcp_tool(
    name="get_project",
    description="Get detailed information about a specific project.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Project ID (format: provider_id:project_key)"
            }
        },
        "required": ["project_id"]
    }
)
class GetProjectTool(PMServiceReadTool):
    """Get project details."""
    
    async def execute(self, project_id: str) -> dict[str, Any]:
        """Get project using PM Service."""
        async with self.client as client:
            return await client.get_project(project_id)
