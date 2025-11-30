"""
Assign Task Tool

Assigns a task to a user.
"""

from typing import Any

from ..base import WriteTool
from ..decorators import mcp_tool


@mcp_tool(
    name="assign_task",
    description="Assign a task to a user.",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "Task ID to assign (format: 'provider_id:task_id')"
            },
            "assignee_id": {
                "type": "string",
                "description": "User ID to assign the task to"
            }
        },
        "required": ["task_id", "assignee_id"]
    }
)
class AssignTaskTool(WriteTool):
    """Assign a task to a user."""
    
    async def execute(self, task_id: str, assignee_id: str, **kwargs) -> dict[str, Any]:
        """
        Assign a task to a user.
        
        Args:
            task_id: Task ID (composite format)
            assignee_id: User ID to assign to
        
        Returns:
            Updated task info
        """
        # Parse task_id
        if ":" not in task_id:
            raise ValueError("task_id must be in format 'provider_id:task_id'")
        
        provider_id, actual_task_id = task_id.split(":", 1)
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        
        # Update task with new assignee
        if hasattr(provider, 'update_task'):
            result = await provider.update_task(
                task_id=actual_task_id,
                assignee_id=assignee_id
            )
            
            task_dict = self._to_dict(result)
            return {
                "success": True,
                "message": f"Task assigned to user {assignee_id}",
                "task": task_dict
            }
        else:
            return {
                "success": False,
                "message": "Task assignment not supported by this provider. Please assign directly in your PM system.",
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


