"""
Delete Task Tool

Deletes a task from PM provider.
"""

from typing import Any

from ..base import WriteTool
from ..decorators import mcp_tool


@mcp_tool(
    name="delete_task",
    description="Delete a task from the PM system.",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "Task ID to delete (format: 'provider_id:task_id')"
            }
        },
        "required": ["task_id"]
    }
)
class DeleteTaskTool(WriteTool):
    """Delete a task."""
    
    async def execute(self, task_id: str, **kwargs) -> dict[str, Any]:
        """
        Delete a task.
        
        Args:
            task_id: Task ID (composite format)
        
        Returns:
            Delete confirmation
        """
        # Parse task_id
        if ":" not in task_id:
            raise ValueError("task_id must be in format 'provider_id:task_id'")
        
        provider_id, actual_task_id = task_id.split(":", 1)
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        
        # Delete task
        if hasattr(provider, 'delete_task'):
            await provider.delete_task(actual_task_id)
            return {
                "success": True,
                "message": f"Task {task_id} deleted successfully",
                "task_id": task_id
            }
        else:
            return {
                "success": False,
                "message": "Task deletion not supported by this provider. Please delete directly in your PM system.",
                "task_id": task_id
            }


