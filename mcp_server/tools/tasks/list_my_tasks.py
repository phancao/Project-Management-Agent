"""
List My Tasks Tool

Lists tasks assigned to the current user across all projects and providers.
"""

from typing import Any

from ..base import ReadTool
from ..decorators import mcp_tool, default_value


@mcp_tool(
    name="list_my_tasks",
    description=(
        "List all tasks assigned to the current user (me) across ALL projects and providers. "
        "This is user-specific - it shows only tasks where you are the assignee. "
        "Use this when the user asks about 'my tasks', 'tasks assigned to me', or 'what should I work on'."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Filter by task status (e.g., 'open', 'in_progress', 'done')"
            },
            "project_id": {
                "type": "string",
                "description": "Optional: Filter by specific project ID (format: 'provider_uuid:project_key')"
            }
        }
    }
)
class ListMyTasksTool(ReadTool):
    """List tasks assigned to the current user."""
    
    async def execute(
        self,
        status: str | None = None,
        project_id: str | None = None
    ) -> dict[str, Any]:
        """
        List tasks assigned to the current user.
        
        Args:
            status: Optional status filter
            project_id: Optional project filter
        
        Returns:
            Dictionary with user's tasks and metadata
        """
        # Get user ID from context
        user_id = self.context.user_id
        
        if not user_id:
            return {
                "tasks": [],
                "total": 0,
                "returned": 0,
                "message": "No user context available. Cannot determine current user."
            }
        
        tasks = []
        
        if project_id:
            # Filter by specific project
            provider_id, actual_project_id = self._parse_project_id(project_id)
            provider = await self.context.provider_manager.get_provider(provider_id)
            provider_conn = self.context.provider_manager.get_provider_by_id(provider_id)
            
            # Get user's tasks in this project
            try:
                # First get user mapping for this provider
                user_mapping = await self._get_user_mapping(provider, user_id)
                
                if user_mapping:
                    raw_tasks = await provider.list_tasks(
                        project_id=actual_project_id,
                        assignee_id=user_mapping
                    )
                    
                    for task in raw_tasks:
                        task_dict = self._to_dict(task)
                        task_dict["provider_id"] = str(provider_conn.id)
                        task_dict["provider_name"] = provider_conn.name
                        tasks.append(task_dict)
            except Exception as e:
                self.context.provider_manager.record_error(str(provider_conn.id), e)
        else:
            # Get tasks from all providers
            providers = self.context.provider_manager.get_active_providers()
            
            for provider_conn in providers:
                try:
                    provider = self.context.provider_manager.create_provider_instance(provider_conn)
                    
                    # Get user mapping for this provider
                    user_mapping = await self._get_user_mapping(provider, user_id)
                    
                    if user_mapping:
                        # Get all projects for this provider
                        projects = await provider.list_projects()
                        
                        for proj in projects:
                            try:
                                project_tasks = await provider.list_tasks(
                                    project_id=str(proj.id),
                                    assignee_id=user_mapping
                                )
                                
                                for task in project_tasks:
                                    task_dict = self._to_dict(task)
                                    task_dict["provider_id"] = str(provider_conn.id)
                                    task_dict["provider_name"] = provider_conn.name
                                    task_dict["project_name"] = proj.name
                                    tasks.append(task_dict)
                            except Exception:
                                continue
                                
                except Exception as e:
                    self.context.provider_manager.record_error(str(provider_conn.id), e)
                    continue
        
        # Filter by status if provided
        if status:
            status_lower = status.lower()
            tasks = [
                t for t in tasks 
                if t.get("status", "").lower() == status_lower
            ]
        
        # Record total
        total = len(tasks)
        
        return {
            "tasks": tasks,
            "total": total,
            "user_id": user_id
        }
    
    async def _get_user_mapping(self, provider, user_id: str) -> str | None:
        """
        Get the provider-specific user ID for our internal user ID.
        
        For now, we try to find the user by email or username match.
        """
        try:
            # Try to get users from provider
            users = await provider.list_users()
            
            # Try to find matching user by ID (some providers use our user IDs)
            for user in users:
                user_dict = self._to_dict(user)
                provider_user_id = str(user_dict.get("id", ""))
                
                # Direct match
                if provider_user_id == user_id:
                    return provider_user_id
            
            # If no direct match found, try by email
            # (In a real system, you'd have a user mapping table)
            # For now, return the user_id and let the provider handle it
            return user_id
            
        except Exception:
            # If we can't get users, just use the user_id directly
            return user_id
    
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


