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
        # Parse project_id (now async to support provider discovery)
        provider_id, actual_project_id = await self._parse_project_id(project_id)
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
    
    async def _parse_project_id(self, project_id: str) -> tuple[str, str]:
        """
        Parse composite project ID.
        
        If project_id has a provider prefix (format: "provider_id:project_id"),
        returns the provider_id and project_id.
        
        If project_id doesn't have a prefix, tries to find which provider
        owns the project by attempting to get the project from each active provider.
        """
        if ":" in project_id:
            return project_id.split(":", 1)
        else:
            # No provider prefix - need to find which provider owns this project
            providers = self.context.provider_manager.get_active_providers()
            if not providers:
                raise ValueError("No active PM providers found")
            
            # Try each provider to find which one has this project
            # This ensures we use the correct provider instead of just the first one
            for provider_conn in providers:
                try:
                    provider = await self.context.provider_manager.get_provider(str(provider_conn.id))
                    # Try to get the project to verify it exists in this provider
                    project = await provider.get_project(project_id)
                    if project:
                        # Found the project in this provider
                        return str(provider_conn.id), project_id
                except Exception:
                    # Project not found in this provider, try next one
                    continue
            
            # If we couldn't find the project in any provider, raise an error
            # This is better than silently using the wrong provider
            provider_names = [p.name for p in providers]
            raise ValueError(
                f"Project '{project_id}' not found in any active provider. "
                f"Active providers: {', '.join(provider_names)}. "
                f"Please ensure the project_id includes the provider prefix (format: 'provider_id:project_id') "
                f"or the project exists in one of the active providers."
            )
    
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

