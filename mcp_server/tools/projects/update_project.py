"""
Update Project Tool

Updates an existing project.
"""

from typing import Any

from ..base import WriteTool
from ..decorators import mcp_tool


@mcp_tool(
    name="update_project",
    description="Update an existing project's name, description, or status.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Project ID (format: 'provider_id:project_key')"
            },
            "name": {
                "type": "string",
                "description": "New project name"
            },
            "description": {
                "type": "string",
                "description": "New project description"
            },
            "status": {
                "type": "string",
                "description": "New project status"
            }
        },
        "required": ["project_id"]
    }
)
class UpdateProjectTool(WriteTool):
    """Update a project."""
    
    async def execute(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        Update a project.
        
        Args:
            project_id: Project ID (composite format)
            name: New name
            description: New description
            status: New status
        
        Returns:
            Updated project info
        """
        # Check at least one update field provided
        if not any([name, description, status]):
            return {
                "success": False,
                "message": "At least one field to update is required (name, description, or status)"
            }
        
        # Parse project_id
        provider_id, actual_project_id = self._parse_project_id(project_id)
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        
        # Update project
        if hasattr(provider, 'update_project'):
            updates = {}
            if name:
                updates["name"] = name
            if description:
                updates["description"] = description
            if status:
                updates["status"] = status
            
            result = await provider.update_project(
                project_id=actual_project_id,
                **updates
            )
            
            project_dict = self._to_dict(result)
            project_dict["provider_id"] = str(provider_conn.id)
            
            return {
                "success": True,
                "message": f"Project updated successfully",
                "project": project_dict
            }
        else:
            return {
                "success": False,
                "message": f"Project update not supported by {provider_conn.provider_type}. Please update directly in your PM system.",
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
    
    def _to_dict(self, obj) -> dict:
        """Convert object to dictionary."""
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        raise TypeError(f"Cannot convert {type(obj).__name__} to dict")


