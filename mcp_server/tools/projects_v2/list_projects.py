"""
List Projects Tool

Lists all accessible projects across all PM providers.
"""

from typing import Any

from ..base import ReadTool
from ..decorators import mcp_tool, default_value


@mcp_tool(
    name="list_projects",
    description=(
        "List all accessible projects across all PM providers. "
        "Returns project information including name, description, status, and provider details. "
        "Use this to discover available projects before performing other operations."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "provider_id": {
                "type": "string",
                "description": "Filter projects by provider ID (optional)"
            },
            "search": {
                "type": "string",
                "description": "Search term for project name/description (optional)"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of projects to return (default: 100)",
                "minimum": 1,
                "maximum": 1000
            }
        }
    }
)
class ListProjectsTool(ReadTool):
    """
    List all accessible projects across all PM providers.
    
    This tool queries all active PM providers and aggregates their projects.
    Results can be filtered by provider, searched by name/description, and limited.
    """
    
    @default_value("limit", 100)
    async def execute(
        self,
        provider_id: str | None = None,
        search: str | None = None,
        limit: int = 100
    ) -> dict[str, Any]:
        """
        List all accessible projects.
        
        Args:
            provider_id: Filter projects by provider ID (optional)
            search: Search term for project name/description (optional)
            limit: Maximum number of projects to return (default: 100)
        
        Returns:
            Dictionary with:
            - projects: List of project objects
            - total: Total number of projects found
            - providers_queried: Number of providers queried
        """
        # Get active providers
        providers = self.context.provider_manager.get_active_providers()
        
        if not providers:
            return {
                "error": "No active PM providers configured",
                "message": (
                    "Please configure at least one PM provider first. "
                    "Call list_providers to check status, then configure_pm_provider to add one."
                ),
                "projects": [],
                "total": 0,
                "providers_queried": 0
            }
        
        # Filter by provider_id if specified
        if provider_id:
            providers = [p for p in providers if str(p.id) == provider_id]
            if not providers:
                return {
                    "error": f"Provider {provider_id} not found or not active",
                    "projects": [],
                    "total": 0,
                    "providers_queried": 0
                }
        
        # Fetch projects from all providers
        all_projects = []
        providers_queried = 0
        
        for provider_conn in providers:
            try:
                # Create provider instance
                provider = self.context.provider_manager.create_provider_instance(provider_conn)
                
                # Fetch projects
                projects = await provider.list_projects()
                
                # Add provider metadata to each project
                for project in projects:
                    project["provider_id"] = str(provider_conn.id)
                    project["provider_name"] = provider_conn.name
                    project["provider_type"] = provider_conn.provider_type
                    project["provider_url"] = provider_conn.base_url
                
                all_projects.extend(projects)
                providers_queried += 1
                
            except Exception as e:
                # Log error but continue with other providers
                self.context.provider_manager.record_error(str(provider_conn.id), e)
                continue
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            all_projects = [
                p for p in all_projects
                if search_lower in p.get("name", "").lower()
                or search_lower in p.get("description", "").lower()
            ]
        
        # Apply limit
        total_found = len(all_projects)
        all_projects = all_projects[:limit]
        
        return {
            "projects": all_projects,
            "total": total_found,
            "returned": len(all_projects),
            "providers_queried": providers_queried,
            "providers_available": len(self.context.provider_manager.get_active_providers())
        }

