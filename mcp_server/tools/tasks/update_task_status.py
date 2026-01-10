"""
Update Task Status Tool

Updates the status of a task.
"""

from typing import Any

from ..base import WriteTool
from ..decorators import mcp_tool


@mcp_tool(
    name="update_task_status",
    description="Update the status of a task (e.g., to 'in_progress', 'done', 'closed').",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "Task ID to update (format: 'provider_id:task_id')"
            },
            "status": {
                "type": "string",
                "description": "New status (e.g., 'open', 'in_progress', 'done', 'closed')"
            }
        },
        "required": ["task_id", "status"]
    }
)
class UpdateTaskStatusTool(WriteTool):
    """Update task status."""
    
    async def execute(self, task_id: str, status: str, **kwargs) -> dict[str, Any]:
        """
        Update task status.
        
        Args:
            task_id: Task ID (composite format)
            status: New status
        
        Returns:
            Updated task info
        """
        # Parse task_id
        if ":" not in task_id:
            raise ValueError("task_id must be in format 'provider_id:task_id'")
        
        provider_id, actual_task_id = task_id.split(":", 1)
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        
        # Update task status
        if hasattr(provider, 'update_task'):
            result = await provider.update_task(
                task_id=actual_task_id,
                status=status
            )
            
            task_dict = self._to_dict(result)
            return {
                "success": True,
                "message": f"Task status updated to '{status}'",
                "task": task_dict
            }
        else:
            return {
                "success": False,
                "message": "Task status update not supported by this provider. Please update directly in your PM system.",
                "task_id": task_id
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


