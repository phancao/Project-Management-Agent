# PM Service Sync Client
"""
Synchronous client for PM Service API.
Wrapper around async client for sync code.
"""

import asyncio
import logging
import os
from typing import Any, Optional

from .async_client import AsyncPMServiceClient

logger = logging.getLogger(__name__)

# Default PM Service URL
DEFAULT_PM_SERVICE_URL = os.environ.get("PM_SERVICE_URL", "http://localhost:8001")


class PMServiceClient:
    """
    Synchronous client for PM Service API.
    
    Wraps AsyncPMServiceClient for use in synchronous code.
    
    Usage:
        client = PMServiceClient()
        projects = client.list_projects()
    """
    
    def __init__(
        self,
        base_url: str = DEFAULT_PM_SERVICE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize sync client.
        
        Args:
            base_url: PM Service base URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
        """
        self._async_client = AsyncPMServiceClient(
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay
        )
    
    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, create a new loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(coro)
    
    # ==================== Health ====================
    
    def health_check(self) -> dict[str, Any]:
        """Check PM Service health."""
        return self._run_async(self._async_client.health_check())
    
    # ==================== Projects ====================
    
    def list_projects(
        self,
        provider_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> dict[str, Any]:
        """List projects."""
        return self._run_async(
            self._async_client.list_projects(
                provider_id=provider_id,
                user_id=user_id,
                limit=limit,
                offset=offset
            )
        )
    
    def get_project(self, project_id: str) -> dict[str, Any]:
        """Get project by ID."""
        return self._run_async(self._async_client.get_project(project_id))
    
    # ==================== Tasks ====================
    
    def list_tasks(
        self,
        project_id: Optional[str] = None,
        sprint_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> dict[str, Any]:
        """List tasks with filters."""
        return self._run_async(
            self._async_client.list_tasks(
                project_id=project_id,
                sprint_id=sprint_id,
                assignee_id=assignee_id,
                status=status,
                limit=limit,
                offset=offset
            )
        )
    
    def get_task(self, task_id: str) -> dict[str, Any]:
        """Get task by ID."""
        return self._run_async(self._async_client.get_task(task_id))
    
    def create_task(
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
        """Create a new task."""
        return self._run_async(
            self._async_client.create_task(
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
        )
    
    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        assignee_id: Optional[str] = None,
        sprint_id: Optional[str] = None,
        story_points: Optional[float] = None,
        priority: Optional[str] = None,
        progress: Optional[int] = None
    ) -> dict[str, Any]:
        """Update a task."""
        return self._run_async(
            self._async_client.update_task(
                task_id=task_id,
                title=title,
                description=description,
                status=status,
                assignee_id=assignee_id,
                sprint_id=sprint_id,
                story_points=story_points,
                priority=priority,
                progress=progress
            )
        )
    
    # ==================== Sprints ====================
    
    def list_sprints(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> dict[str, Any]:
        """List sprints."""
        return self._run_async(
            self._async_client.list_sprints(
                project_id=project_id,
                status=status,
                limit=limit
            )
        )
    
    def get_sprint(self, sprint_id: str) -> dict[str, Any]:
        """Get sprint by ID."""
        return self._run_async(self._async_client.get_sprint(sprint_id))
    
    def get_sprint_tasks(self, sprint_id: str, limit: int = 100) -> dict[str, Any]:
        """Get tasks in a sprint."""
        return self._run_async(
            self._async_client.get_sprint_tasks(sprint_id, limit=limit)
        )
    
    # ==================== Users ====================
    
    def list_users(
        self,
        project_id: Optional[str] = None,
        limit: int = 100
    ) -> dict[str, Any]:
        """List users."""
        return self._run_async(
            self._async_client.list_users(project_id=project_id, limit=limit)
        )
    
    def get_user(self, user_id: str) -> dict[str, Any]:
        """Get user by ID."""
        return self._run_async(self._async_client.get_user(user_id))
    
    # ==================== Providers ====================
    
    def list_providers(self) -> dict[str, Any]:
        """List configured providers."""
        return self._run_async(self._async_client.list_providers())
    
    def get_provider(self, provider_id: str) -> dict[str, Any]:
        """Get provider by ID."""
        return self._run_async(self._async_client.get_provider(provider_id))
    
    def sync_provider(
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
        """Sync provider configuration from backend."""
        return self._run_async(
            self._async_client.sync_provider(
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
        )
    
    def delete_provider(self, provider_id: str) -> dict[str, Any]:
        """Delete a provider."""
        return self._run_async(self._async_client.delete_provider(provider_id))

