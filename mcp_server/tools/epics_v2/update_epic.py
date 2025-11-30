"""
Update Epic Tool

Updates an existing epic.
"""

from typing import Any

from ..base import WriteTool
from ..decorators import mcp_tool


@mcp_tool(
    name="update_epic",
    description="Update an existing epic's name, description, or status.",
    input_schema={
        "type": "object",
        "properties": {
            "epic_id": {
                "type": "string",
                "description": "Epic ID (format: 'provider_id:epic_id')"
            },
            "name": {
                "type": "string",
                "description": "New epic name"
            },
            "description": {
                "type": "string",
                "description": "New epic description"
            },
            "status": {
                "type": "string",
                "description": "New epic status"
            }
        },
        "required": ["epic_id"]
    }
)
class UpdateEpicTool(WriteTool):
    """Update an epic."""
    
    async def execute(
        self,
        epic_id: str,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        Update an epic.
        
        Args:
            epic_id: Epic ID (composite format)
            name: New name
            description: New description
            status: New status
        
        Returns:
            Updated epic info
        """
        # Check at least one update field provided
        if not any([name, description, status]):
            return {
                "success": False,
                "message": "At least one field to update is required"
            }
        
        # Parse epic_id
        if ":" not in epic_id:
            raise ValueError("epic_id must be in format 'provider_id:epic_id'")
        
        provider_id, actual_epic_id = epic_id.split(":", 1)
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        
        # Update epic
        if hasattr(provider, 'update_epic'):
            updates = {}
            if name:
                updates["name"] = name
            if description:
                updates["description"] = description
            if status:
                updates["status"] = status
            
            result = await provider.update_epic(
                epic_id=actual_epic_id,
                **updates
            )
            
            epic_dict = self._to_dict(result)
            epic_dict["provider_id"] = str(provider_conn.id)
            
            return {
                "success": True,
                "message": "Epic updated successfully",
                "epic": epic_dict
            }
        else:
            return {
                "success": False,
                "message": f"Epic update not supported by {provider_conn.provider_type}. Please update directly in your PM system.",
                "epic_id": epic_id
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


