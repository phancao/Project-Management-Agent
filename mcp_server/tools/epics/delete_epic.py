"""
Delete Epic Tool

Deletes an epic from PM provider.
"""

from typing import Any

from ..base import WriteTool
from ..decorators import mcp_tool


@mcp_tool(
    name="delete_epic",
    description="Delete an epic.",
    input_schema={
        "type": "object",
        "properties": {
            "epic_id": {
                "type": "string",
                "description": "Epic ID to delete (format: 'provider_id:epic_id')"
            }
        },
        "required": ["epic_id"]
    }
)
class DeleteEpicTool(WriteTool):
    """Delete an epic."""
    
    async def execute(self, epic_id: str, **kwargs) -> dict[str, Any]:
        """
        Delete an epic.
        
        Args:
            epic_id: Epic ID (composite format)
        
        Returns:
            Delete confirmation
        """
        # Parse epic_id
        if ":" not in epic_id:
            raise ValueError("epic_id must be in format 'provider_id:epic_id'")
        
        provider_id, actual_epic_id = epic_id.split(":", 1)
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        
        # Delete epic
        if hasattr(provider, 'delete_epic'):
            await provider.delete_epic(actual_epic_id)
            return {
                "success": True,
                "message": f"Epic {epic_id} deleted successfully",
                "epic_id": epic_id
            }
        else:
            return {
                "success": False,
                "message": f"Epic deletion not supported by {provider_conn.provider_type}. Please delete directly in your PM system.",
                "epic_id": epic_id
            }


