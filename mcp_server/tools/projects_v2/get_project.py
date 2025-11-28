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
        
        # Convert PMProject to dict if needed
        project_dict = self._to_dict(project)
    
    def _to_dict(self, obj) -> dict:
        """Convert object to dictionary."""
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        # For Pydantic BaseModel objects that may not have model_dump
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        raise TypeError(f"Cannot convert {type(obj).__name__} to dict")
        
        # Add provider metadata
        provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        if provider_conn:
            project_dict["provider_id"] = str(provider_conn.id)
            project_dict["provider_name"] = provider_conn.name
            project_dict["provider_type"] = provider_conn.provider_type
            project_dict["provider_url"] = provider_conn.base_url
        
        return project_dict
    
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

