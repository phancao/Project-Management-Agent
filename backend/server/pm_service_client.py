# Backend PM Service Client
"""
PM Service client wrapper for Backend API.
Provides the same interface as the old PMHandler but uses PM Service.
"""

import logging
import os
from typing import Any, Optional

from pm_service.client import AsyncPMServiceClient

logger = logging.getLogger(__name__)

# PM Service URL
PM_SERVICE_URL = os.environ.get("PM_SERVICE_URL", "http://localhost:8001")


class PMServiceHandler:
    """
    PM Service handler for Backend API.
    
    Provides the same interface as the old PMHandler but uses PM Service API.
    """
    
    def __init__(self, user_id: Optional[str] = None):
        """
        Initialize handler.
        
        Args:
            user_id: Optional user ID for filtering
        """
        self.user_id = user_id
        self._client = AsyncPMServiceClient(base_url=PM_SERVICE_URL)
        # For compatibility with PM tools that expect single_provider
        self.single_provider = self
    
    @classmethod
    def from_db_session(cls, db_session=None, user_id: Optional[str] = None):
        """
        Create handler, loading PM Service URL from provider configuration.
        
        Uses the PM Service API to get providers and find pm_service_url,
        since the backend API can't directly access the MCP Server database.
        
        Args:
            db_session: Ignored - uses PM Service API instead
            user_id: Optional user ID
            
        Returns:
            PMServiceHandler instance
        """
        import httpx
        
        # First, try to get PM Service URL from PM Service API
        # Use default URL to make initial API call
        default_pm_service_url = PM_SERVICE_URL
        pm_service_url = default_pm_service_url
        
        try:
            # Use sync client since we are in a sync method and potentially in a running event loop
            with httpx.Client(timeout=5.0) as client:
                try:
                    # Get providers from PM Service API
                    response = client.get(f"{default_pm_service_url}/api/v1/providers")
                    if response.status_code == 200:
                        providers = response.json().get("items", [])
                        # Find first provider with pm_service_url
                        for provider in providers:
                            additional_config = provider.get("additional_config", {})
                            if isinstance(additional_config, dict):
                                url = additional_config.get("pm_service_url")
                                if url:
                                    logger.info(f"Found PM Service URL from provider {provider.get('id')}: {url}")
                                    pm_service_url = url
                                    break
                except Exception as e:
                    logger.warning(f"Failed to get PM Service URL from API: {e}, using default: {default_pm_service_url}")
        except Exception as e:
            logger.warning(f"Error getting PM Service URL from API: {e}, using default: {default_pm_service_url}")
            pm_service_url = default_pm_service_url
        
        instance = cls(user_id=user_id)
        # Update client with the loaded URL
        instance._client = AsyncPMServiceClient(base_url=pm_service_url)
        return instance
    
    # ==================== Projects ====================
    
    async def list_all_projects(self) -> list[dict[str, Any]]:
        """List all projects from all providers."""
        async with self._client as client:
            result = await client.list_projects(user_id=self.user_id)
        return result.get("items", [])
    
    async def get_project(self, project_id: str) -> Optional[dict[str, Any]]:
        """Get project by ID."""
        async with self._client as client:
            try:
                return await client.get_project(project_id)
            except Exception as e:
                logger.error(f"Failed to get project {project_id}: {e}")
                return None
    
    # ==================== Tasks ====================
    
    async def list_project_tasks(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """List tasks in a project."""
        async with self._client as client:
            result = await client.list_tasks(
                project_id=project_id,
                sprint_id=sprint_id,
                assignee_id=assignee_id,
                status=status
            )
        return result.get("items", [])
    
    async def list_my_tasks(self) -> list[dict[str, Any]]:
        """List tasks assigned to current user."""
        async with self._client as client:
            result = await client.list_tasks(assignee_id=self.user_id)
        return result.get("items", [])
    
    async def list_all_tasks(
        self,
        project_id: Optional[str] = None,
        assignee_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """List all tasks from all providers."""
        async with self._client as client:
            result = await client.list_tasks(
                project_id=project_id,
                assignee_id=assignee_id
            )
        return result.get("items", [])
    
    async def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        """Get task by ID."""
        async with self._client as client:
            try:
                return await client.get_task(task_id)
            except Exception as e:
                logger.error(f"Failed to get task {task_id}: {e}")
                return None
    
    async def create_project_task(
        self,
        project_id: str,
        task_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a task in a project."""
        async with self._client as client:
            return await client.create_task(
                project_id=project_id,
                title=task_data.get("title", ""),
                description=task_data.get("description"),
                assignee_id=task_data.get("assignee_id"),
                sprint_id=task_data.get("sprint_id"),
                story_points=task_data.get("story_points"),
                priority=task_data.get("priority"),
                task_type=task_data.get("task_type") or task_data.get("type"),
                parent_id=task_data.get("parent_id")
            )
    
    async def update_task(
        self,
        task_id: str,
        **updates
    ) -> Optional[dict[str, Any]]:
        """Update a task."""
        async with self._client as client:
            try:
                return await client.update_task(task_id, **updates)
            except Exception as e:
                logger.error(f"Failed to update task {task_id}: {e}")
                return None
    
    async def assign_task_to_user(
        self,
        project_id: str,
        task_id: str,
        assignee_id: Optional[str]
    ) -> dict[str, Any]:
        """Assign task to user."""
        async with self._client as client:
            return await client.update_task(task_id, assignee_id=assignee_id)
    
    async def assign_task_to_sprint(
        self,
        project_id: str,
        task_id: str,
        sprint_id: str
    ) -> dict[str, Any]:
        """Assign task to sprint."""
        async with self._client as client:
            return await client.update_task(task_id, sprint_id=sprint_id)
    
    async def move_task_to_backlog(
        self,
        project_id: str,
        task_id: str
    ) -> dict[str, Any]:
        """Move task to backlog (remove from sprint)."""
        async with self._client as client:
            return await client.update_task(task_id, sprint_id=None)
    
    async def assign_task_to_epic(
        self,
        project_id: str,
        task_id: str,
        epic_id: str
    ) -> dict[str, Any]:
        """Assign task to epic."""
        async with self._client as client:
            return await client.update_task(task_id, epic_id=epic_id)
    
    async def remove_task_from_epic(
        self,
        project_id: str,
        task_id: str
    ) -> dict[str, Any]:
        """Remove task from epic."""
        async with self._client as client:
            return await client.update_task(task_id, epic_id=None)
    
    # ==================== Sprints ====================
    
    async def list_sprints(
        self,
        project_id: str,
        status: Optional[str] = None,
        state: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """List sprints in a project (compatible with both old and new API)."""
        # Use state if provided (for backward compatibility)
        sprint_status = state or status
        logger.info(f"[PMServiceHandler] list_sprints called: project_id={project_id}, status={sprint_status}")
        
        import time
        start_time = time.time()
        
        async with self._client as client:
            result = await client.list_sprints(
                project_id=project_id,
                status=sprint_status
            )
            
        duration = time.time() - start_time
        logger.info(f"[PMServiceHandler] ⏱️ UPSTREAM list_sprints call took {duration:.2f}s")
        
        items = result.get("items", [])
        total = result.get("total", len(items))
        returned = result.get("returned", len(items))
        logger.info(
            f"[PMServiceHandler] list_sprints result: {len(items)} items, "
            f"total={total}, returned={returned}"
        )
        # Check for duplicates
        sprint_ids = [item.get("id") for item in items if isinstance(item, dict)]
        unique_ids = set(sprint_ids)
        if len(sprint_ids) != len(unique_ids):
            logger.warning(
                f"[PMServiceHandler] ⚠️ DUPLICATES in PM Service response: "
                f"{len(sprint_ids)} items, {len(unique_ids)} unique IDs"
            )
        return items
    
    async def list_all_sprints(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """List all sprints (optionally filtered by project)."""
        return await self.list_sprints(project_id=project_id or "", status=status)
    
    async def list_project_sprints(
        self,
        project_id: str,
        status: Optional[str] = None,
        state: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """List sprints in a project (legacy method name)."""
        return await self.list_sprints(project_id=project_id, status=status, state=state)
    
    async def get_sprint(self, sprint_id: str) -> Optional[dict[str, Any]]:
        """Get sprint by ID."""
        async with self._client as client:
            try:
                return await client.get_sprint(sprint_id)
            except Exception as e:
                logger.error(f"Failed to get sprint {sprint_id}: {e}")
                return None
    
    # ==================== Epics ====================
    
    async def list_project_epics(
        self,
        project_id: str
    ) -> list[dict[str, Any]]:
        """List epics in a project."""
        async with self._client as client:
            result = await client.list_epics(project_id=project_id)
        return result.get("items", [])
    
    async def get_epic(self, epic_id: str) -> Optional[dict[str, Any]]:
        """Get epic by ID."""
        async with self._client as client:
            try:
                return await client.get_epic(epic_id)
            except Exception as e:
                logger.error(f"Failed to get epic {epic_id}: {e}")
                return None
    
    async def create_project_epic(
        self,
        project_id: str,
        epic_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create an epic in a project."""
        async with self._client as client:
            return await client.create_epic(
                project_id=project_id,
                name=epic_data.get("name", ""),
                description=epic_data.get("description"),
                color=epic_data.get("color")
            )
    
    async def update_project_epic(
        self,
        project_id: str,
        epic_id: str,
        updates: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an epic."""
        async with self._client as client:
            return await client.update_epic(epic_id, **updates)
    
    async def delete_project_epic(
        self,
        project_id: str,
        epic_id: str
    ) -> bool:
        """Delete an epic."""
        async with self._client as client:
            try:
                await client.delete_epic(epic_id)
                return True
            except Exception as e:
                logger.error(f"Failed to delete epic {epic_id}: {e}")
                return False
    
    # ==================== Users ====================
    
    async def list_project_users(
        self,
        project_id: str
    ) -> list[dict[str, Any]]:
        """List users in a project."""
        async with self._client as client:
            result = await client.list_users(project_id=project_id)
        return result.get("items", [])
    
    async def get_user(self, user_id: str) -> Optional[dict[str, Any]]:
        """Get user by ID."""
        async with self._client as client:
            try:
                return await client.get_user(user_id)
            except Exception as e:
                logger.error(f"Failed to get user {user_id}: {e}")
                return None
    
    # ==================== Providers ====================
    
    async def list_providers(self) -> list[dict[str, Any]]:
        """List all providers."""
        async with self._client as client:
            result = await client.list_providers()
        return result.get("items", [])
    
    async def sync_provider(
        self,
        backend_provider_id: str,
        provider_type: str,
        name: str,
        base_url: str,
        api_key: Optional[str] = None,
        api_token: Optional[str] = None,
        username: Optional[str] = None,
        is_active: bool = True,
        additional_config: Optional[dict] = None
    ) -> dict[str, Any]:
        """Sync provider configuration to PM Service."""
        async with self._client as client:
            return await client.sync_provider(
                backend_provider_id=backend_provider_id,
                provider_type=provider_type,
                name=name,
                base_url=base_url,
                api_key=api_key,
                api_token=api_token,
                username=username,
                is_active=is_active,
                additional_config=additional_config
            )
    
    # ==================== Timeline & Analytics ====================
    
    async def get_project_timeline(
        self,
        project_id: str
    ) -> dict[str, Any]:
        """Get project timeline data (sprints + tasks)."""
        sprints = await self.list_project_sprints(project_id)
        tasks = await self.list_project_tasks(project_id)
        
        return {
            "sprints": sprints,
            "tasks": tasks,
            "project_id": project_id
        }
    
    # ==================== Labels & Statuses ====================
    
    async def list_project_labels(
        self,
        project_id: str
    ) -> list[dict[str, Any]]:
        """List labels/tags in a project."""
        # Labels are not yet implemented in PM Service
        # Return empty list for now
        logger.warning(f"list_project_labels not implemented, returning empty list")
        return []
    
    async def list_project_statuses(
        self,
        project_id: str,
        entity_type: str = "task"
    ) -> list[dict[str, Any]]:
        """List available statuses for a project."""
        async with self._client as client:
            result = await client.list_statuses(
                project_id=project_id,
                entity_type=entity_type
            )
        return result.get("items", [])
    
    async def list_project_priorities(
        self,
        project_id: str
    ) -> list[dict[str, Any]]:
        """List available priorities for a project."""
        async with self._client as client:
            result = await client.list_priorities(project_id=project_id)
        return result.get("items", [])


# Convenience function
def get_pm_service_handler(user_id: Optional[str] = None) -> PMServiceHandler:
    """Get PM Service handler instance."""
    return PMServiceHandler(user_id=user_id)


# Alias for backward compatibility
PMHandler = PMServiceHandler
