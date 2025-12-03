"""
List Unassigned Tasks Tool

Lists tasks that are not assigned to any user in a project.
Useful for identifying work that needs to be assigned.
"""

from typing import Any

from ..base import ReadTool
from ..decorators import mcp_tool, require_project


@mcp_tool(
    name="list_unassigned_tasks",
    description=(
        "List tasks that are not assigned to any user in a project. "
        "Use this to identify unassigned work that needs to be distributed. "
        "This is useful for resource allocation analysis."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Project ID (format: 'provider_uuid:project_key')"
            },
            "status": {
                "type": "string",
                "description": "Optional: Filter by task status (e.g., 'To Do', 'In Progress', 'Done')"
            }
        },
        "required": ["project_id"]
    }
)
class ListUnassignedTasksTool(ReadTool):
    """List tasks that are not assigned to any user."""
    
    @require_project
    async def execute(
        self,
        project_id: str,
        status: str | None = None
    ) -> dict[str, Any]:
        """
        List unassigned tasks.
        
        Args:
            project_id: Project ID (format: "provider_uuid:project_key")
            status: Optional status filter
        
        Returns:
            Dictionary with unassigned tasks and metadata
        """
        # Parse project_id
        provider_id, actual_project_id = self._parse_project_id(project_id)
        provider = await self.context.provider_manager.get_provider(provider_id)
        
        # Get all tasks for the project
        all_tasks = await provider.list_tasks(
            project_id=actual_project_id
        )
        
        # Filter for unassigned tasks (no assignee_id or assignee_id is None/empty)
        unassigned_tasks = [
            task for task in all_tasks 
            if not task.assignee_id or task.assignee_id == "" or task.assignee_id is None
        ]
        
        # Filter by status if provided
        if status:
            unassigned_tasks = [
                task for task in unassigned_tasks 
                if task.status and task.status.lower() == status.lower()
            ]
        
        # Convert to dicts and add provider metadata
        provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        tasks = []
        for task in unassigned_tasks:
            task_dict = self._to_dict(task)
            task_dict["provider_id"] = str(provider_conn.id)
            task_dict["provider_name"] = provider_conn.name
            tasks.append(task_dict)
        
        return {
            "tasks": tasks,
            "total": len(tasks),
            "returned": len(tasks),
            "project_id": project_id,
            "note": "These tasks are not assigned to any user"
        }
    
    def _parse_project_id(self, project_id: str) -> tuple[str, str]:
        """Parse composite project ID."""
        if ":" in project_id:
            return project_id.split(":", 1)
        else:
            providers = self.context.provider_manager.get_active_providers()
            if not providers:
                raise ValueError("No active PM providers found")
            return str(providers[0].id), project_id
    
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

