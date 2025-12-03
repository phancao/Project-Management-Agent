"""
List Tasks by Assignee Tool

Lists tasks assigned to a specific user in a project.
This is more efficient than list_tasks for workload analysis as it returns only tasks for one assignee.
"""

from typing import Any

from ..base import ReadTool
from ..decorators import mcp_tool, require_project


@mcp_tool(
    name="list_tasks_by_assignee",
    description=(
        "List tasks assigned to a specific user in a project. "
        "Use this for workload analysis - it returns only tasks for one assignee, "
        "which is much more efficient than listing all tasks. "
        "After listing users with list_users, call this tool for each user to check their workload."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Project ID (format: 'provider_uuid:project_key')"
            },
            "assignee_id": {
                "type": "string",
                "description": "User ID of the assignee to filter by"
            },
            "status": {
                "type": "string",
                "description": "Optional: Filter by task status (e.g., 'To Do', 'In Progress', 'Done')"
            }
        },
        "required": ["project_id", "assignee_id"]
    }
)
class ListTasksByAssigneeTool(ReadTool):
    """List tasks assigned to a specific user."""
    
    @require_project
    async def execute(
        self,
        project_id: str,
        assignee_id: str,
        status: str | None = None
    ) -> dict[str, Any]:
        """
        List tasks assigned to a specific user.
        
        Args:
            project_id: Project ID (format: "provider_uuid:project_key")
            assignee_id: User ID of the assignee
            status: Optional status filter
        
        Returns:
            Dictionary with tasks and metadata
        """
        # Parse project_id
        provider_id, actual_project_id = self._parse_project_id(project_id)
        provider = await self.context.provider_manager.get_provider(provider_id)
        
        # Get tasks for this assignee
        raw_tasks = await provider.list_tasks(
            project_id=actual_project_id,
            assignee_id=assignee_id
        )
        
        # Filter by status if provided
        if status:
            raw_tasks = [
                task for task in raw_tasks 
                if task.status and task.status.lower() == status.lower()
            ]
        
        # Convert to dicts and add provider metadata
        provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        tasks = []
        for task in raw_tasks:
            task_dict = self._to_dict(task)
            task_dict["provider_id"] = str(provider_conn.id)
            task_dict["provider_name"] = provider_conn.name
            tasks.append(task_dict)
        
        return {
            "tasks": tasks,
            "total": len(tasks),
            "returned": len(tasks),
            "assignee_id": assignee_id,
            "project_id": project_id
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

