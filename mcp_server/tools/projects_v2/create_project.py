"""
Create Project Tool

Creates a new project in PM provider.
"""

from typing import Any

from ..base import WriteTool
from ..decorators import mcp_tool


@mcp_tool(
    name="create_project",
    description="Create a new project. Note: Project creation may not be supported by all providers.",
    input_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Project name"
            },
            "description": {
                "type": "string",
                "description": "Project description"
            },
            "provider_id": {
                "type": "string",
                "description": "Provider ID to create project in (uses first available if not specified)"
            }
        },
        "required": ["name"]
    }
)
class CreateProjectTool(WriteTool):
    """Create a new project."""
    
    async def execute(
        self,
        name: str,
        description: str | None = None,
        provider_id: str | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        Create a new project.
        
        Args:
            name: Project name
            description: Project description
            provider_id: Provider to create in
        
        Returns:
            Created project info
        """
        # Get provider
        if provider_id:
            provider = await self.context.provider_manager.get_provider(provider_id)
            provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        else:
            providers = self.context.provider_manager.get_active_providers()
            if not providers:
                raise ValueError("No active PM providers found")
            provider_conn = providers[0]
            provider = self.context.provider_manager.create_provider_instance(provider_conn)
        
        # Create project
        if hasattr(provider, 'create_project'):
            result = await provider.create_project(
                name=name,
                description=description
            )
            
            project_dict = self._to_dict(result)
            project_dict["provider_id"] = str(provider_conn.id)
            project_dict["provider_name"] = provider_conn.name
            
            return {
                "success": True,
                "message": f"Project '{name}' created successfully",
                "project": project_dict
            }
        else:
            return {
                "success": False,
                "message": f"Project creation not supported by {provider_conn.provider_type}. Please create projects directly in your PM system.",
                "provider": provider_conn.provider_type
            }
    
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


