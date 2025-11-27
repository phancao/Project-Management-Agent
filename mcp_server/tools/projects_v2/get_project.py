"""
Get Project Tool

Retrieves detailed information about a specific project.
"""

from typing import Any

from ..base import ReadTool
from ..decorators import mcp_tool, require_project


@mcp_tool(
    name="get_project",
    description=(
        "Get detailed information about a specific project. "
        "Returns comprehensive project details including name, description, status, "
        "members, settings, and provider-specific metadata."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Project ID (format: 'provider_uuid:project_key' or just 'project_key')"
            }
        },
        "required": ["project_id"]
    }
)
class GetProjectTool(ReadTool):
    """
    Get detailed information about a specific project.
    
    Retrieves comprehensive project details from the PM provider.
    """
    
    @require_project
    async def execute(self, project_id: str) -> dict[str, Any]:
        """
        Get project details.
        
        Args:
            project_id: Project ID (format: "provider_uuid:project_key" or "project_key")
        
        Returns:
            Project details dictionary
        """
        # Parse composite project ID
        provider_id, actual_project_id = self._parse_project_id(project_id)
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        
        # Get project details
        project = await provider.get_project(actual_project_id)
        
        # Add provider metadata
        provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        if provider_conn:
            project["provider_id"] = str(provider_conn.id)
            project["provider_name"] = provider_conn.name
            project["provider_type"] = provider_conn.provider_type
            project["provider_url"] = provider_conn.base_url
        
        return project
    
    def _parse_project_id(self, project_id: str) -> tuple[str, str]:
        """
        Parse composite project ID.
        
        Args:
            project_id: Project ID (may be composite "provider_id:project_key")
        
        Returns:
            Tuple of (provider_id, actual_project_id)
        """
        if ":" in project_id:
            provider_id, actual_project_id = project_id.split(":", 1)
            return provider_id, actual_project_id
        else:
            # Fallback: get first active provider
            providers = self.context.provider_manager.get_active_providers()
            if not providers:
                raise ValueError("No active PM providers found")
            return str(providers[0].id), project_id

