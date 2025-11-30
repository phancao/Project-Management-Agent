"""
Create Epic Tool

Creates a new epic in PM provider.
"""

from typing import Any

from ..base import WriteTool
from ..decorators import mcp_tool


@mcp_tool(
    name="create_epic",
    description="Create a new epic in a project.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Project ID (format: 'provider_id:project_key')"
            },
            "name": {
                "type": "string",
                "description": "Epic name"
            },
            "description": {
                "type": "string",
                "description": "Epic description"
            }
        },
        "required": ["project_id", "name"]
    }
)
class CreateEpicTool(WriteTool):
    """Create a new epic."""
    
    async def execute(
        self,
        project_id: str,
        name: str,
        description: str | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        Create a new epic.
        
        Args:
            project_id: Project ID (composite format)
            name: Epic name
            description: Epic description
        
        Returns:
            Created epic info
        """
        # Parse project_id
        provider_id, actual_project_id = self._parse_project_id(project_id)
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        
        # Create epic
        if hasattr(provider, 'create_epic'):
            result = await provider.create_epic(
                project_id=actual_project_id,
                name=name,
                description=description
            )
            
            epic_dict = self._to_dict(result)
            epic_dict["provider_id"] = str(provider_conn.id)
            
            return {
                "success": True,
                "message": f"Epic '{name}' created successfully",
                "epic": epic_dict
            }
        else:
            return {
                "success": False,
                "message": f"Epic creation not supported by {provider_conn.provider_type}. Please create epics directly in your PM system.",
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


