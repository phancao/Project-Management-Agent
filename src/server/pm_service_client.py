# Backend PM Service Client
"""
PM Service client wrapper for Backend API.
Provides the same interface as PMHandler but uses PM Service.
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
    
    Provides similar interface to PMHandler but uses PM Service API.
    This allows gradual migration from direct provider calls to PM Service.
    """
    
    def __init__(self, user_id: Optional[str] = None):
        """
        Initialize handler.
        
        Args:
            user_id: Optional user ID for filtering
        """
        self.user_id = user_id
        self._client = AsyncPMServiceClient(base_url=PM_SERVICE_URL)
    
    @classmethod
    def from_db_session(cls, db_session=None, user_id: Optional[str] = None):
        """
        Create handler (db_session ignored, kept for compatibility).
        
        Args:
            db_session: Ignored (for compatibility with PMHandler)
            user_id: Optional user ID
            
        Returns:
            PMServiceHandler instance
        """
        return cls(user_id=user_id)
    
    # ==================== Projects ====================
    
    async def list_all_projects(self) -> list[dict[str, Any]]:
        """List all projects."""
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
        title: str,
        description: Optional[str] = None,
        assignee_id: Optional[str] = None,
        sprint_id: Optional[str] = None,
        story_points: Optional[float] = None,
        priority: Optional[str] = None,
        task_type: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Create a task in a project."""
        async with self._client as client:
            return await client.create_task(
                project_id=project_id,
                title=title,
                description=description,
                assignee_id=assignee_id,
                sprint_id=sprint_id,
                story_points=story_points,
                priority=priority,
                task_type=task_type,
                parent_id=parent_id
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
    
    # ==================== Sprints ====================
    
    async def list_project_sprints(
        self,
        project_id: str,
        status: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """List sprints in a project."""
        async with self._client as client:
            result = await client.list_sprints(
                project_id=project_id,
                status=status
            )
        return result.get("items", [])
    
    async def get_sprint(self, sprint_id: str) -> Optional[dict[str, Any]]:
        """Get sprint by ID."""
        async with self._client as client:
            try:
                return await client.get_sprint(sprint_id)
            except Exception as e:
                logger.error(f"Failed to get sprint {sprint_id}: {e}")
                return None
    
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


# Convenience function
def get_pm_service_handler(user_id: Optional[str] = None) -> PMServiceHandler:
    """Get PM Service handler instance."""
    return PMServiceHandler(user_id=user_id)

