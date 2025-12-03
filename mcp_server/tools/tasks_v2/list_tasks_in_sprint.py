"""
List Tasks in Sprint Tool

Lists tasks assigned to a specific sprint.
This is more efficient than list_tasks for sprint analysis as it returns only tasks for one sprint.
"""

from typing import Any, Optional

from ..base import ReadTool
from ..decorators import mcp_tool


@mcp_tool(
    name="list_tasks_in_sprint",
    description=(
        "List tasks assigned to a specific sprint. "
        "Use this for sprint analysis - it returns only tasks for one sprint, "
        "which is more efficient than listing all tasks. "
        "After getting sprint_id from list_sprints, call this tool to get all tasks in that sprint."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "sprint_id": {
                "type": "string",
                "description": "Sprint ID (format: 'provider_uuid:sprint_key' or numeric ID like '613')"
            },
            "project_id": {
                "type": "string",
                "description": "Optional project ID (format: 'provider_uuid:project_key'). If not provided, will be extracted from sprint."
            },
            "assignee_id": {
                "type": "string",
                "description": "Optional: Filter by assignee user ID (to get tasks for a specific user in the sprint)"
            },
            "status": {
                "type": "string",
                "description": "Optional: Filter by task status (e.g., 'To Do', 'In Progress', 'Done')"
            }
        },
        "required": ["sprint_id"]
    }
)
class ListTasksInSprintTool(ReadTool):
    """List tasks assigned to a specific sprint."""
    
    async def execute(
        self,
        sprint_id: str,
        project_id: str | None = None,
        assignee_id: str | None = None,
        status: str | None = None
    ) -> dict[str, Any]:
        """
        List tasks in a sprint.
        
        Args:
            sprint_id: Sprint ID (composite format or numeric)
            project_id: Optional project ID (will be extracted from sprint if not provided)
            assignee_id: Optional assignee filter
            status: Optional status filter
        
        Returns:
            Dictionary with tasks and metadata
        """
        # Parse sprint_id
        if ":" in sprint_id:
            provider_id, actual_sprint_id = sprint_id.split(":", 1)
        else:
            # If no provider prefix, try to get from project_id or use first active provider
            if project_id and ":" in project_id:
                provider_id, _ = project_id.split(":", 1)
            else:
                providers = self.context.provider_manager.get_active_providers()
                if not providers:
                    raise ValueError("No active PM providers found and sprint_id is not in composite format")
                provider_id = str(providers[0].id)
            actual_sprint_id = sprint_id
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        
        # Get project_id if not provided (from sprint)
        if not project_id:
            try:
                sprint = await provider.get_sprint(actual_sprint_id)
                sprint_dict = self._to_dict(sprint)
                project_id = sprint_dict.get("project_id")
                if project_id:
                    # Make it composite if not already
                    if ":" not in str(project_id):
                        project_id = f"{provider_id}:{project_id}"
            except Exception as e:
                self.context.logger.warning(f"Could not get project_id from sprint: {e}")
        
        # Get tasks
        if project_id:
            # Parse project_id
            _, actual_project_id = self._parse_project_id(project_id)
            
            # Get all tasks for the project
            raw_tasks = await provider.list_tasks(
                project_id=actual_project_id,
                assignee_id=assignee_id
            )
            
            # Filter by sprint
            sprint_tasks = [
                task for task in raw_tasks 
                if self._task_in_sprint(task, actual_sprint_id)
            ]
        else:
            # Fallback: get all tasks and filter by sprint
            providers = self.context.provider_manager.get_active_providers()
            sprint_tasks = []
            
            for provider_conn in providers:
                try:
                    provider = self.context.provider_manager.create_provider_instance(provider_conn)
                    all_tasks = await provider.list_tasks(assignee_id=assignee_id)
                    provider_tasks = [
                        task for task in all_tasks 
                        if self._task_in_sprint(task, actual_sprint_id)
                    ]
                    sprint_tasks.extend(provider_tasks)
                except Exception as e:
                    self.context.provider_manager.record_error(str(provider_conn.id), e)
                    continue
        
        # Filter by status if provided
        if status:
            sprint_tasks = [
                task for task in sprint_tasks 
                if task.status and task.status.lower() == status.lower()
            ]
        
        # Convert to dicts and add provider metadata
        tasks = []
        for task in sprint_tasks:
            task_dict = self._to_dict(task)
            task_dict["provider_id"] = str(provider_conn.id)
            task_dict["provider_name"] = provider_conn.name
            tasks.append(task_dict)
        
        return {
            "tasks": tasks,
            "total": len(tasks),
            "returned": len(tasks),
            "sprint_id": sprint_id,
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
    
    def _task_in_sprint(self, task, sprint_id: str) -> bool:
        """Check if a task belongs to a sprint."""
        task_dict = self._to_dict(task) if not isinstance(task, dict) else task
        
        # Check version/sprint field (OpenProject uses 'version')
        task_sprint = task_dict.get("sprint_id") or task_dict.get("version_id") or task_dict.get("version")
        if task_sprint:
            # Handle dict format like {"id": 613, "name": "Sprint 4"}
            if isinstance(task_sprint, dict):
                task_sprint_id = str(task_sprint.get("id", ""))
            else:
                task_sprint_id = str(task_sprint)
            
            # Extract numeric part if composite
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

