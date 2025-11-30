"""
Search Projects Tool

Searches projects by name or description.
"""

from typing import Any

from ..base import ReadTool
from ..decorators import mcp_tool, default_value


@mcp_tool(
    name="search_projects",
    description="Search projects by name or description across all providers.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query to match against project name or description"
            },
            "provider_id": {
                "type": "string",
                "description": "Optional: Filter by provider ID"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results (default: 10)"
            }
        },
        "required": ["query"]
    }
)
class SearchProjectsTool(ReadTool):
    """Search projects by query."""
    
    @default_value("limit", 10)
    async def execute(
        self,
        query: str,
        provider_id: str | None = None,
        limit: int = 10,
        **kwargs
    ) -> dict[str, Any]:
        """
        Search projects.
        
        Args:
            query: Search query
            provider_id: Optional provider filter
            limit: Maximum results
        
        Returns:
            Matching projects
        """
        query_lower = query.lower()
        all_projects = []
        
        if provider_id:
            # Search in specific provider
            provider = await self.context.provider_manager.get_provider(provider_id)
            provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
            
            projects = await provider.list_projects()
            
            for project in projects:
                project_dict = self._to_dict(project)
                project_dict["provider_id"] = str(provider_conn.id)
                project_dict["provider_name"] = provider_conn.name
                all_projects.append(project_dict)
        else:
            # Search across all providers
            providers = self.context.provider_manager.get_active_providers()
            
            for provider_conn in providers:
                try:
                    provider = self.context.provider_manager.create_provider_instance(provider_conn)
                    projects = await provider.list_projects()
                    
                    for project in projects:
                        project_dict = self._to_dict(project)
                        project_dict["provider_id"] = str(provider_conn.id)
                        project_dict["provider_name"] = provider_conn.name
                        all_projects.append(project_dict)
                except Exception as e:
                    self.context.provider_manager.record_error(str(provider_conn.id), e)
                    continue
        
        # Filter by query
        matching_projects = [
            p for p in all_projects
            if query_lower in p.get("name", "").lower()
            or query_lower in (p.get("description") or "").lower()
        ]
        
        # Apply limit
        matching_projects = matching_projects[:limit]
        
        return {
            "projects": matching_projects,
            "total": len(matching_projects),
            "query": query
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


