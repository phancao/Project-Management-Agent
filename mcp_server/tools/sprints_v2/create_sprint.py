"""
Create Sprint Tool

Creates a new sprint in PM provider.
"""

from typing import Any

from ..base import WriteTool
from ..decorators import mcp_tool


@mcp_tool(
    name="create_sprint",
    description="Create a new sprint in a project.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Project ID (format: 'provider_id:project_key')"
            },
            "name": {
                "type": "string",
                "description": "Sprint name"
            },
            "start_date": {
                "type": "string",
                "description": "Start date (YYYY-MM-DD)"
            },
            "end_date": {
                "type": "string",
                "description": "End date (YYYY-MM-DD)"
            },
            "goal": {
                "type": "string",
                "description": "Sprint goal"
            }
        },
        "required": ["project_id", "name", "start_date", "end_date"]
    }
)
class CreateSprintTool(WriteTool):
    """Create a new sprint."""
    
    async def execute(
        self,
        project_id: str,
        name: str,
        start_date: str,
        end_date: str,
        goal: str | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        Create a new sprint.
        
        Args:
            project_id: Project ID (composite format)
            name: Sprint name
            start_date: Start date
            end_date: End date
            goal: Sprint goal
        
        Returns:
            Created sprint info
        """
        # Parse project_id
        provider_id, actual_project_id = self._parse_project_id(project_id)
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
        
        # Create sprint
        if hasattr(provider, 'create_sprint'):
            result = await provider.create_sprint(
                project_id=actual_project_id,
                name=name,
                start_date=start_date,
                end_date=end_date,
                goal=goal
            )
            
            sprint_dict = self._to_dict(result)
            sprint_dict["provider_id"] = str(provider_conn.id)
            
            return {
                "success": True,
                "message": f"Sprint '{name}' created successfully",
                "sprint": sprint_dict
            }
        else:
            return {
                "success": False,
                "message": f"Sprint creation not supported by {provider_conn.provider_type}. Please create sprints directly in your PM system.",
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


