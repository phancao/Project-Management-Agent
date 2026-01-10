"""
Update Sprint Tool

Updates an existing sprint.
"""

from typing import Any

from ..base import WriteTool
from ..decorators import mcp_tool


@mcp_tool(
    name="update_sprint",
    description="Update an existing sprint's name, dates, or goal.",
    input_schema={
        "type": "object",
        "properties": {
            "sprint_id": {
                "type": "string",
                "description": "Sprint ID (format: 'provider_id:sprint_id')"
            },
            "name": {
                "type": "string",
                "description": "New sprint name"
            },
            "start_date": {
                "type": "string",
                "description": "New start date (YYYY-MM-DD)"
            },
            "end_date": {
                "type": "string",
                "description": "New end date (YYYY-MM-DD)"
            },
            "goal": {
                "type": "string",
                "description": "New sprint goal"
            },
            "status": {
                "type": "string",
                "description": "New status"
            }
        },
        "required": ["sprint_id"]
    }
)
class UpdateSprintTool(WriteTool):
    """Update a sprint."""
    
    async def execute(
        self,
        sprint_id: str,
        name: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        goal: str | None = None,
        status: str | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        Update a sprint.
        
        Args:
            sprint_id: Sprint ID (composite format)
            name: New name
            start_date: New start date
            end_date: New end date
            goal: New goal
            status: New status
        
        Returns:
            Updated sprint info
        """
        # Check at least one update field provided
        if not any([name, start_date, end_date, goal, status]):
            return {
                "success": False,
                "message": "At least one field to update is required"
            }
        
        # Parse sprint_id
        if ":" not in sprint_id:
            raise ValueError("sprint_id must be in format 'provider_id:sprint_id'")
        
        provider_id, actual_sprint_id = sprint_id.split(":", 1)
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        
        # Update sprint
        if hasattr(provider, 'update_sprint'):
            updates = {}
            if name:
                updates["name"] = name
            if start_date:
                updates["start_date"] = start_date
            if end_date:
                updates["end_date"] = end_date
            if goal:
                updates["goal"] = goal
            if status:
                updates["status"] = status
            
            result = await provider.update_sprint(
                sprint_id=actual_sprint_id,
                **updates
            )
            
            sprint_dict = self._to_dict(result)
            sprint_dict["provider_id"] = str(provider_conn.id)
            
            return {
                "success": True,
                "message": "Sprint updated successfully",
                "sprint": sprint_dict
            }
        else:
            return {
                "success": False,
                "message": f"Sprint update not supported by {provider_conn.provider_type}. Please update directly in your PM system.",
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


