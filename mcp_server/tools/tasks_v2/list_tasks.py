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
        "Supports filtering by project, assignee, status, and more. "
        "Returns task information including title, status, assignee, and dates."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Filter by project ID (format: 'provider_uuid:project_key')"
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
                "description": "Maximum number of tasks to return (default: 100)"
            }
        }
    }
)
class ListTasksTool(ReadTool):
    """List tasks with filtering options."""
    
    @default_value("limit", 100)
    async def execute(
        self,
        project_id: str | None = None,
        assignee_id: str | None = None,
        status: str | None = None,
        limit: int = 100
    ) -> dict[str, Any]:
        """
        List tasks.
        
        Args:
            project_id: Filter by project ID
            assignee_id: Filter by assignee
            status: Filter by status
            limit: Maximum results
        
        Returns:
            Dictionary with tasks and metadata
        """
        # Parse project_id if provided
        if project_id:
            provider_id, actual_project_id = self._parse_project_id(project_id)
            provider = await self.context.provider_manager.get_provider(provider_id)
            
            # Get tasks from specific project
            raw_tasks = await provider.list_tasks(
                project_id=actual_project_id,
                assignee_id=assignee_id
            )
            
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
                    
                    # Convert to dicts and add provider metadata
                    for task in provider_tasks:
                        task_dict = self._to_dict(task)
                        task_dict["provider_id"] = str(provider_conn.id)
                        task_dict["provider_name"] = provider_conn.name
                        tasks.append(task_dict)
                except Exception as e:
                    self.context.provider_manager.record_error(str(provider_conn.id), e)
                    continue
        
        # Apply limit
        total = len(tasks)
        tasks = tasks[:limit]
        
        return {
            "tasks": tasks,
            "total": total,
            "returned": len(tasks)
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
        return dict(obj)

