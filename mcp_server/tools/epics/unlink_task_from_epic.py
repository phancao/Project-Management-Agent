"""
Unlink Task from Epic Tool

Unlinks a task from an epic.
"""

from typing import Any

from ..base import WriteTool
from ..decorators import mcp_tool


@mcp_tool(
    name="unlink_task_from_epic",
    description="Unlink a task from an epic.",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "Task ID (format: 'provider_id:task_id')"
            }
        },
        "required": ["task_id"]
    }
)
class UnlinkTaskFromEpicTool(WriteTool):
    """Unlink a task from an epic."""
    
    async def execute(self, task_id: str, **kwargs) -> dict[str, Any]:
        """
        Unlink a task from an epic.
        
        Args:
            task_id: Task ID (composite format)
        
        Returns:
            Updated task info
        """
        # Parse task_id
        if ":" not in task_id:
            raise ValueError("task_id must be in format 'provider_id:task_id'")
        
        provider_id, actual_task_id = task_id.split(":", 1)
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        
        # Unlink task from epic
        if hasattr(provider, 'unlink_task_from_epic'):
            result = await provider.unlink_task_from_epic(actual_task_id)
            task_dict = self._to_dict(result)
            task_dict["provider_id"] = str(provider_conn.id)
            
            return {
                "success": True,
                "message": "Task unlinked from epic",
                "task": task_dict
            }
        elif hasattr(provider, 'update_task'):
            # Fallback: try to update task with epic_id=None
            result = await provider.update_task(
                task_id=actual_task_id,
                epic_id=None
            )
            task_dict = self._to_dict(result)
            task_dict["provider_id"] = str(provider_conn.id)
            
            return {
                "success": True,
                "message": "Task unlinked from epic",
                "task": task_dict
            }
        else:
            return {
                "success": False,
                "message": f"Unlinking task from epic not supported by {provider_conn.provider_type}. Please unlink directly in your PM system.",
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


