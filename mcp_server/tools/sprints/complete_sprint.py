"""
Complete Sprint Tool

Completes a sprint (changes status to closed).
"""

from typing import Any

from ..base import WriteTool
from ..decorators import mcp_tool


@mcp_tool(
    name="complete_sprint",
    description="Complete a sprint (change status to closed).",
    input_schema={
        "type": "object",
        "properties": {
            "sprint_id": {
                "type": "string",
                "description": "Sprint ID to complete (format: 'provider_id:sprint_id')"
            }
        },
        "required": ["sprint_id"]
    }
)
class CompleteSprintTool(WriteTool):
    """Complete a sprint."""
    
    async def execute(self, sprint_id: str, **kwargs) -> dict[str, Any]:
        """
        Complete a sprint.
        
        Args:
            sprint_id: Sprint ID (composite format)
        
        Returns:
            Updated sprint info
        """
        # Parse sprint_id
        if ":" not in sprint_id:
            raise ValueError("sprint_id must be in format 'provider_id:sprint_id'")
        
        provider_id, actual_sprint_id = sprint_id.split(":", 1)
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        
        # Complete sprint
        if hasattr(provider, 'complete_sprint'):
            result = await provider.complete_sprint(actual_sprint_id)
            sprint_dict = self._to_dict(result)
            sprint_dict["provider_id"] = str(provider_conn.id)
            
            return {
                "success": True,
                "message": "Sprint completed successfully",
                "sprint": sprint_dict
            }
        elif hasattr(provider, 'update_sprint'):
            # Fallback: try to update status to closed
            result = await provider.update_sprint(
                sprint_id=actual_sprint_id,
                status="closed"
            )
            sprint_dict = self._to_dict(result)
            sprint_dict["provider_id"] = str(provider_conn.id)
            
            return {
                "success": True,
                "message": "Sprint completed successfully",
                "sprint": sprint_dict
            }
        else:
            return {
                "success": False,
                "message": f"Sprint completion not supported by {provider_conn.provider_type}. Please complete directly in your PM system.",
                "sprint_id": sprint_id
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


