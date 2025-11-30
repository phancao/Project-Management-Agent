"""
Get Sprint Tasks Tool

Gets all tasks in a sprint.
"""

from typing import Any

from ..base import ReadTool
from ..decorators import mcp_tool


@mcp_tool(
    name="get_sprint_tasks",
    description="Get all tasks in a sprint.",
    input_schema={
        "type": "object",
        "properties": {
            "sprint_id": {
                "type": "string",
                "description": "Sprint ID (format: 'provider_id:sprint_id')"
            }
        },
        "required": ["sprint_id"]
    }
)
class GetSprintTasksTool(ReadTool):
    """Get tasks in a sprint."""
    
    async def execute(self, sprint_id: str, **kwargs) -> dict[str, Any]:
        """
        Get tasks in a sprint.
        
        Args:
            sprint_id: Sprint ID (composite format)
        
        Returns:
            Tasks in the sprint
        """
        # Parse sprint_id
        if ":" not in sprint_id:
            raise ValueError("sprint_id must be in format 'provider_id:sprint_id'")
        
        provider_id, actual_sprint_id = sprint_id.split(":", 1)
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        
        # Get sprint tasks
        if hasattr(provider, 'get_sprint_tasks'):
            tasks = await provider.get_sprint_tasks(actual_sprint_id)
        else:
            # Fallback: get all tasks and filter by sprint
            # First get the sprint to get project_id
            sprint = await provider.get_sprint(actual_sprint_id)
            sprint_dict = self._to_dict(sprint)
            project_id = sprint_dict.get("project_id")
            
            if project_id:
                all_tasks = await provider.list_tasks(project_id=project_id)
                tasks = [
                    t for t in all_tasks
                    if self._task_in_sprint(t, actual_sprint_id)
                ]
            else:
                tasks = []
        
        # Convert to dicts
        task_list = []
        for task in tasks:
            task_dict = self._to_dict(task)
            task_dict["provider_id"] = str(provider_conn.id)
            task_list.append(task_dict)
        
        return {
            "tasks": task_list,
            "total": len(task_list),
            "sprint_id": sprint_id
        }
    
    def _task_in_sprint(self, task, sprint_id: str) -> bool:
        """Check if a task belongs to a sprint."""
        task_dict = self._to_dict(task) if not isinstance(task, dict) else task
        
        task_sprint = task_dict.get("sprint_id") or task_dict.get("version_id") or task_dict.get("version")
        if task_sprint:
            if isinstance(task_sprint, dict):
                task_sprint_id = str(task_sprint.get("id", ""))
            else:
                task_sprint_id = str(task_sprint)
            
            if ":" in task_sprint_id:
                task_sprint_id = task_sprint_id.split(":", 1)[1]
            
            return task_sprint_id == sprint_id
        
        return False
    
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


