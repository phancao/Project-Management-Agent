"""
Delete Project Tool

Deletes a project from PM provider.
"""

from typing import Any

from ..base import WriteTool
from ..decorators import mcp_tool


@mcp_tool(
    name="delete_project",
    description="Delete a project. Warning: This action cannot be undone.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Project ID to delete (format: 'provider_id:project_key')"
            }
        },
        "required": ["project_id"]
    }
)
class DeleteProjectTool(WriteTool):
    """Delete a project."""
    
    async def execute(self, project_id: str, **kwargs) -> dict[str, Any]:
        """
        Delete a project.
        
        Args:
            project_id: Project ID (composite format)
        
        Returns:
            Delete confirmation
        """
        # Parse project_id
        provider_id, actual_project_id = self._parse_project_id(project_id)
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        
        # Delete project
        if hasattr(provider, 'delete_project'):
            await provider.delete_project(actual_project_id)
            return {
                "success": True,
                "message": f"Project {project_id} deleted successfully",
                "project_id": project_id
            }
        else:
            return {
                "success": False,
                "message": f"Project deletion not supported by {provider_conn.provider_type}. Please delete directly in your PM system.",
                "project_id": project_id
            }
    
    def _parse_project_id(self, project_id: str) -> tuple[str, str]:
        """Parse composite project ID."""
        if ":" in project_id:
            return project_id.split(":", 1)
        else:
            providers = self.context.provider_manager.get_active_providers()
            if not providers:
                raise ValueError("No active PM providers found")
            return str(providers[0].id), project_id


