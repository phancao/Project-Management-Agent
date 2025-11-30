"""
Delete Sprint Tool

Deletes a sprint from PM provider.
"""

from typing import Any

from ..base import WriteTool
from ..decorators import mcp_tool


@mcp_tool(
    name="delete_sprint",
    description="Delete a sprint.",
    input_schema={
        "type": "object",
        "properties": {
            "sprint_id": {
                "type": "string",
                "description": "Sprint ID to delete (format: 'provider_id:sprint_id')"
            }
        },
        "required": ["sprint_id"]
    }
)
class DeleteSprintTool(WriteTool):
    """Delete a sprint."""
    
    async def execute(self, sprint_id: str, **kwargs) -> dict[str, Any]:
        """
        Delete a sprint.
        
        Args:
            sprint_id: Sprint ID (composite format)
        
        Returns:
            Delete confirmation
        """
        # Parse sprint_id
        if ":" not in sprint_id:
            raise ValueError("sprint_id must be in format 'provider_id:sprint_id'")
        
        provider_id, actual_sprint_id = sprint_id.split(":", 1)
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        
        # Delete sprint
        if hasattr(provider, 'delete_sprint'):
            await provider.delete_sprint(actual_sprint_id)
            return {
                "success": True,
                "message": f"Sprint {sprint_id} deleted successfully",
                "sprint_id": sprint_id
            }
        else:
            return {
                "success": False,
                "message": f"Sprint deletion not supported by {provider_conn.provider_type}. Please delete directly in your PM system.",
                "sprint_id": sprint_id
            }


