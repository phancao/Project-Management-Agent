"""
PM Provider Integration for Meeting Agent.

Connects meeting action items to PM systems like OpenProject.
"""

from typing import Any, Dict, List, Optional
import logging

from shared.handlers.base import HandlerContext, HandlerResult

logger = logging.getLogger(__name__)


class MeetingPMIntegration:
    """
    Integrates meeting action items with PM systems.
    
    Uses the existing PM provider infrastructure from the backend.
    """
    
    def __init__(self, pm_service=None):
        """
        Initialize PM integration.
        
        Args:
            pm_service: Optional PM service instance (from backend.pm_providers)
        """
        self._pm_service = pm_service
        self._provider_cache = {}
    
    async def get_pm_service(self):
        """Get or initialize PM service"""
        if self._pm_service is None:
            try:
                from backend.pm_providers import PMService
                self._pm_service = PMService()
            except ImportError:
                logger.warning("PM providers not available")
                return None
        return self._pm_service
    
    async def create_task_from_action_item(
        self,
        action_item,
        project_id: str,
        provider_id: Optional[str] = None,
    ) -> HandlerResult[Dict[str, Any]]:
        """
        Create a PM task from an action item.
        
        Args:
            action_item: ActionItem to convert
            project_id: Target project (format: provider:project_key or just project_key)
            provider_id: Optional explicit provider ID
            
        Returns:
            HandlerResult with created task info
        """
        pm_service = await self.get_pm_service()
        
        if not pm_service:
            return HandlerResult.failure("PM service not available")
        
        try:
            # Parse project ID
            if ":" in project_id and not provider_id:
                provider_id, project_key = project_id.split(":", 1)
            else:
                project_key = project_id
                provider_id = provider_id or "openproject"  # Default
            
            # Get provider
            provider = await pm_service.get_provider(provider_id)
            if not provider:
                return HandlerResult.failure(f"Provider not found: {provider_id}")
            
            # Build task data
            task_data = action_item.to_pm_task_data()
            
            # Map assignee if possible
            if action_item.assignee_name and not action_item.assignee_id:
                assignee_id = await self._resolve_assignee(
                    provider, project_key, action_item.assignee_name
                )
                if assignee_id:
                    task_data["assignee_id"] = assignee_id
            
            # Create task in PM system
            task = await provider.create_task(project_key, task_data)
            
            return HandlerResult.success(
                {
                    "task_id": task.id,
                    "task_url": getattr(task, "url", None) or getattr(task, "web_url", None),
                    "title": task.title,
                    "provider": provider_id,
                    "project": project_key,
                },
                message=f"Created task: {task.title}",
            )
            
        except Exception as e:
            logger.exception(f"Failed to create task: {e}")
            return HandlerResult.failure(f"Failed to create task: {str(e)}")
    
    async def create_tasks_bulk(
        self,
        action_items: List,
        project_id: str,
        provider_id: Optional[str] = None,
    ) -> HandlerResult[List[Dict[str, Any]]]:
        """
        Create multiple tasks from action items.
        
        Args:
            action_items: List of ActionItem objects
            project_id: Target project
            provider_id: Optional provider ID
            
        Returns:
            HandlerResult with list of created tasks
        """
        created = []
        errors = []
        
        for item in action_items:
            result = await self.create_task_from_action_item(
                item, project_id, provider_id
            )
            
            if result.is_success:
                created.append(result.data)
                # Update action item with task info
                item.pm_task_id = result.data["task_id"]
                item.pm_task_url = result.data.get("task_url")
            else:
                errors.append(f"{item.description[:50]}: {result.message}")
        
        if not created and errors:
            return HandlerResult.failure(
                f"Failed to create all {len(action_items)} tasks",
                errors=errors,
            )
        elif errors:
            return HandlerResult.partial(
                created,
                warnings=errors,
                message=f"Created {len(created)}/{len(action_items)} tasks",
            )
        else:
            return HandlerResult.success(
                created,
                message=f"Created {len(created)} tasks",
            )
    
    async def _resolve_assignee(
        self,
        provider,
        project_key: str,
        assignee_name: str,
    ) -> Optional[str]:
        """
        Try to resolve an assignee name to a PM user ID.
        
        Looks up users in the project and tries to match by name.
        """
        try:
            users = await provider.list_users(project_key)
            
            # Try exact match first
            for user in users:
                if user.name.lower() == assignee_name.lower():
                    return user.id
            
            # Try partial match
            assignee_lower = assignee_name.lower()
            for user in users:
                if assignee_lower in user.name.lower():
                    return user.id
            
            # Try email match if available
            for user in users:
                if hasattr(user, 'email') and user.email:
                    if assignee_lower in user.email.lower().split('@')[0]:
                        return user.id
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to resolve assignee {assignee_name}: {e}")
            return None
    
    async def get_project_users(
        self,
        project_id: str,
        provider_id: Optional[str] = None,
    ) -> HandlerResult[List[Dict[str, Any]]]:
        """
        Get users in a project for assignee selection.
        """
        pm_service = await self.get_pm_service()
        
        if not pm_service:
            return HandlerResult.failure("PM service not available")
        
        try:
            if ":" in project_id and not provider_id:
                provider_id, project_key = project_id.split(":", 1)
            else:
                project_key = project_id
                provider_id = provider_id or "openproject"
            
            provider = await pm_service.get_provider(provider_id)
            if not provider:
                return HandlerResult.failure(f"Provider not found: {provider_id}")
            
            users = await provider.list_users(project_key)
            
            return HandlerResult.success([
                {
                    "id": u.id,
                    "name": u.name,
                    "email": getattr(u, "email", None),
                }
                for u in users
            ])
            
        except Exception as e:
            logger.exception(f"Failed to get users: {e}")
            return HandlerResult.failure(f"Failed to get users: {str(e)}")
    
    async def list_projects(
        self,
        provider_id: Optional[str] = None,
    ) -> HandlerResult[List[Dict[str, Any]]]:
        """
        List available projects for task creation.
        """
        pm_service = await self.get_pm_service()
        
        if not pm_service:
            return HandlerResult.failure("PM service not available")
        
        try:
            provider_id = provider_id or "openproject"
            provider = await pm_service.get_provider(provider_id)
            
            if not provider:
                return HandlerResult.failure(f"Provider not found: {provider_id}")
            
            projects = await provider.list_projects()
            
            return HandlerResult.success([
                {
                    "id": f"{provider_id}:{p.id}",
                    "key": p.id,
                    "name": p.name,
                    "provider": provider_id,
                }
                for p in projects
            ])
            
        except Exception as e:
            logger.exception(f"Failed to list projects: {e}")
            return HandlerResult.failure(f"Failed to list projects: {str(e)}")
