"""
Search Tasks Tool

Searches tasks across projects by query.
"""

from typing import Any

from ..base import ReadTool
from ..decorators import mcp_tool, default_value


@mcp_tool(
    name="search_tasks",
    description="Search tasks across projects by title or description.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query to match against task title or description"
            },
            "project_id": {
                "type": "string",
                "description": "Optional: Filter by project ID"
            },
            "status": {
                "type": "string",
                "description": "Optional: Filter by status"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results (default: 20)"
            }
        },
        "required": ["query"]
    }
)
class SearchTasksTool(ReadTool):
    """Search tasks by query."""
    
    @default_value("limit", 20)
    async def execute(
        self,
        query: str,
        project_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
        **kwargs
    ) -> dict[str, Any]:
        """
        Search tasks.
        
        Args:
            query: Search query
            project_id: Optional project filter
            status: Optional status filter
            limit: Maximum results
        
        Returns:
            Matching tasks
        """
        query_lower = query.lower()
        all_tasks = []
        
        if project_id:
            # Search in specific project
            provider_id, actual_project_id = self._parse_project_id(project_id)
            provider = await self.context.provider_manager.get_provider(provider_id)
            provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
            
            tasks = await provider.list_tasks(project_id=actual_project_id)
            
            for task in tasks:
                task_dict = self._to_dict(task)
                task_dict["provider_id"] = str(provider_conn.id)
                task_dict["provider_name"] = provider_conn.name
                all_tasks.append(task_dict)
        else:
            # Search across all providers
            providers = self.context.provider_manager.get_active_providers()
            
            for provider_conn in providers:
                try:
                    provider = self.context.provider_manager.create_provider_instance(provider_conn)
                    tasks = await provider.list_tasks()
                    
                    for task in tasks:
                        task_dict = self._to_dict(task)
                        task_dict["provider_id"] = str(provider_conn.id)
                        task_dict["provider_name"] = provider_conn.name
                        all_tasks.append(task_dict)
                except Exception as e:
                    self.context.provider_manager.record_error(str(provider_conn.id), e)
                    continue
        
        # Filter by query
        matching_tasks = [
            t for t in all_tasks
            if query_lower in (t.get("title") or t.get("subject") or "").lower()
            or query_lower in (t.get("description") or "").lower()
        ]
        
        # Filter by status
        if status:
            status_lower = status.lower()
            matching_tasks = [
                t for t in matching_tasks
                if t.get("status", "").lower() == status_lower
            ]
        
        # Apply limit
        matching_tasks = matching_tasks[:limit]
        
        return {
            "tasks": matching_tasks,
            "total": len(matching_tasks),
            "query": query
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


