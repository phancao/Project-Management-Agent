"""
List Tasks Tool

Lists tasks from PM providers with filtering options.
"""

from typing import Any

from ..base import ReadTool
from ..decorators import mcp_tool, default_value


@mcp_tool(
    name="list_tasks",
    description=(
        "List tasks from PM providers. "
        "Supports filtering by project, assignee, sprint, status, and more. "
        "Returns task information including title, status, assignee, and dates."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Filter by project ID (format: 'provider_uuid:project_key')"
            },
            "sprint_id": {
                "type": "string",
                "description": "Filter by sprint ID (numeric ID like '613' or composite like 'provider_id:613')"
            },
            "assignee_id": {
                "type": "string",
                "description": "Filter by assignee user ID"
            },
            "status": {
                "type": "string",
                "description": "Filter by task status"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of tasks to return (default: 50, max: 100)"
            }
        }
    }
)
class ListTasksTool(ReadTool):
    """List tasks with filtering options."""
    
    @default_value("limit", 50)
    async def execute(
        self,
        project_id: str | None = None,
        sprint_id: str | None = None,
        assignee_id: str | None = None,
        status: str | None = None,
        limit: int = 50
    ) -> dict[str, Any]:
        """
        List tasks.
        
        Args:
            project_id: Filter by project ID
            sprint_id: Filter by sprint ID
            assignee_id: Filter by assignee
            status: Filter by status
            limit: Maximum results
        
        Returns:
            Dictionary with tasks and metadata
        """
        # Parse sprint_id if provided (extract numeric part)
        actual_sprint_id = None
        if sprint_id:
            if ":" in sprint_id:
                actual_sprint_id = sprint_id.split(":", 1)[1]
            else:
                actual_sprint_id = sprint_id
            
            # SMART RESOLUTION: If sprint_id is 1-2 digits, it's likely a sprint NUMBER not ID
            # Sprint IDs in OpenProject are typically 3+ digits (like 613, 615)
            # Sprint numbers are 1-2 digits (like "4", "6")
            if actual_sprint_id.isdigit() and len(actual_sprint_id) <= 2 and project_id:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"[list_tasks] Smart resolution: sprint_id '{actual_sprint_id}' looks like a sprint number, resolving to actual ID")
                try:
                    # Parse project_id to get provider
                    provider_id, actual_project_id = self._parse_project_id(project_id)
                    provider = await self.context.provider_manager.get_provider(provider_id)
                    
                    # Fetch sprints and find matching one by name
                    sprints = await provider.list_sprints(project_id=actual_project_id)
                    for sprint in sprints:
                        sprint_dict = self._to_dict(sprint) if not isinstance(sprint, dict) else sprint
                        sprint_name = sprint_dict.get("name", "")
                        # Match if name ends with the number (e.g., "Sprint 6" matches "6")
                        if sprint_name.lower().endswith(f"sprint {actual_sprint_id}") or sprint_name == f"Sprint {actual_sprint_id}":
                            resolved_id = str(sprint_dict.get("id", ""))
                            logger.info(f"[list_tasks] Smart resolution: Resolved sprint '{sprint_name}' (number {actual_sprint_id}) to ID {resolved_id}")
                            actual_sprint_id = resolved_id
                            break
                    else:
                        logger.warning(f"[list_tasks] Smart resolution: Could not find sprint with number {actual_sprint_id}")
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"[list_tasks] Smart resolution failed: {e}")
        
        # Parse project_id if provided
        if project_id:
            provider_id, actual_project_id = self._parse_project_id(project_id)
            provider = await self.context.provider_manager.get_provider(provider_id)
            
            # Get tasks from specific project
            raw_tasks = await provider.list_tasks(
                project_id=actual_project_id,
                assignee_id=assignee_id
            )
            
            # Filter by sprint_id if provided (client-side filtering since OpenProject doesn't support it directly)
            if actual_sprint_id:
                raw_tasks = [
                    task for task in raw_tasks 
                    if self._task_in_sprint(task, actual_sprint_id)
                ]
            
            # Convert to dicts and add provider metadata
            provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
            tasks = []
            for task in raw_tasks:
                task_dict = self._to_dict(task)
                task_dict["provider_id"] = str(provider_conn.id)
                task_dict["provider_name"] = provider_conn.name
                tasks.append(task_dict)
            
        else:
            # Get tasks from all providers
            providers = self.context.provider_manager.get_active_providers()
            tasks = []
            
            for provider_conn in providers:
                try:
                    provider = self.context.provider_manager.create_provider_instance(provider_conn)
                    provider_tasks = await provider.list_tasks(
                        assignee_id=assignee_id
                    )
                    
                    # Filter by sprint_id if provided
                    if actual_sprint_id:
                        provider_tasks = [
                            task for task in provider_tasks 
                            if self._task_in_sprint(task, actual_sprint_id)
                        ]
                    
                    # Convert to dicts and add provider metadata
                    for task in provider_tasks:
                        task_dict = self._to_dict(task)
                        task_dict["provider_id"] = str(provider_conn.id)
                        task_dict["provider_name"] = provider_conn.name
                        tasks.append(task_dict)
                except Exception as e:
                    self.context.provider_manager.record_error(str(provider_conn.id), e)
                    continue
        
        # Apply limit (cap at 100 max to prevent buffer overflow)
        total = len(tasks)
        effective_limit = min(limit, 100)
        tasks = tasks[:effective_limit]
        
        return {
            "tasks": tasks,
            "total": total,
            "returned": len(tasks),
            "sprint_filter": actual_sprint_id
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
        # Try to get sprint info from task
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
        # For Pydantic BaseModel objects that may not have model_dump
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        raise TypeError(f"Cannot convert {type(obj).__name__} to dict")

