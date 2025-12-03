# PM Service Async Client
"""
Async client for PM Service API.
Provides async methods for all PM Service endpoints.
"""

import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# Default PM Service URL
DEFAULT_PM_SERVICE_URL = os.environ.get("PM_SERVICE_URL", "http://localhost:8001")


class AsyncPMServiceClient:
    """
    Async client for PM Service API.
    
    Usage:
        async with AsyncPMServiceClient() as client:
            projects = await client.list_projects()
    """
    
    def __init__(
        self,
        base_url: str = DEFAULT_PM_SERVICE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize async client.
        
        Args:
            base_url: PM Service base URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "AsyncPMServiceClient":
        """Enter async context."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client, creating one if needed."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
        return self._client
    
    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method
            path: API path
            params: Query parameters
            json: JSON body
            
        Returns:
            Response JSON
            
        Raises:
            httpx.HTTPError: On request failure after retries
        """
        import asyncio
        
        client = self._get_client()
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = await client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                # Don't retry 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    logger.error(f"Client error: {e.response.status_code} - {e.response.text}")
                    # Convert 403 errors to PermissionError for better error handling
                    if e.response.status_code == 403:
                        error_text = e.response.text or "Permission denied"
                        raise PermissionError(
                            f"PM Service API returned 403 Forbidden: {error_text}. "
                            "This indicates insufficient permissions. "
                            "Please check your API token permissions or contact your administrator."
                        ) from e
                    raise
                last_error = e
                
            except httpx.RequestError as e:
                last_error = e
            
            # Wait before retry
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Request failed, retrying in {delay}s: {last_error}")
                await asyncio.sleep(delay)
        
        logger.error(f"Request failed after {self.max_retries} attempts: {last_error}")
        raise last_error
    
    async def _paginate_all(
        self,
        path: str,
        params: Optional[dict] = None,
        page_size: int = 500
    ) -> dict[str, Any]:
        """
        Fetch ALL items from a paginated endpoint by iterating through pages.
        
        Args:
            path: API path
            params: Additional query parameters
            page_size: Number of items per page (default: 500)
            
        Returns:
            Combined ListResponse with all items
        """
        all_items = []
        offset = 0
        total = None
        
        base_params = params.copy() if params else {}
        
        while True:
            # Build params for this page
            page_params = {**base_params, "limit": page_size, "offset": offset}
            
            # Fetch page
            result = await self._request("GET", path, params=page_params)
            
            items = result.get("items", [])
            returned = result.get("returned", len(items))
            total = result.get("total", total)
            
            all_items.extend(items)
            
            logger.debug(
                f"Pagination: fetched {returned} items (offset={offset}, "
                f"total so far={len(all_items)}, reported total={total})"
            )
            
            # Check if we have all items
            if returned < page_size:
                # Last page (fewer items than page size)
                break
            
            if total is not None and len(all_items) >= total:
                # We have all items based on reported total
                break
            
            # Move to next page
            offset += page_size
            
            # Safety limit to prevent infinite loops
            if offset > 50000:
                logger.warning(f"Pagination safety limit reached at offset {offset}")
                break
        
        return {
            "items": all_items,
            "total": len(all_items),
            "returned": len(all_items),
            "offset": 0,
            "limit": len(all_items)
        }
    
    # ==================== Health ====================
    
    async def health_check(self) -> dict[str, Any]:
        """Check PM Service health."""
        return await self._request("GET", "/health")
    
    # ==================== Projects ====================
    
    async def list_projects(
        self,
        provider_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        List ALL projects from all providers.
        
        Automatically paginates to fetch all projects.
        
        Args:
            provider_id: Filter by provider ID
            user_id: Filter by user ID
            
        Returns:
            ListResponse with ALL projects
        """
        params = {}
        if provider_id:
            params["provider_id"] = provider_id
        if user_id:
            params["user_id"] = user_id
        
        return await self._paginate_all("/api/v1/projects", params=params)
    
    async def get_project(self, project_id: str) -> dict[str, Any]:
        """
        Get project by ID.
        
        Args:
            project_id: Project ID (composite format: provider_id:project_id)
            
        Returns:
            Project details
        """
        return await self._request("GET", f"/api/v1/projects/{project_id}")
    
    # ==================== Tasks ====================
    
    async def list_tasks(
        self,
        project_id: Optional[str] = None,
        sprint_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> dict[str, Any]:
        """
        List ALL tasks with filters.
        
        Automatically paginates to fetch all tasks.
        
        Args:
            project_id: Filter by project ID
            sprint_id: Filter by sprint ID
            assignee_id: Filter by assignee ID
            status: Filter by status
            
        Returns:
            ListResponse with ALL matching tasks
        """
        params = {}
        if project_id:
            params["project_id"] = project_id
        if sprint_id:
            params["sprint_id"] = sprint_id
        if assignee_id:
            params["assignee_id"] = assignee_id
        if status:
            params["status"] = status
        
        return await self._paginate_all("/api/v1/tasks", params=params)
    
    async def get_task(self, task_id: str) -> dict[str, Any]:
        """
        Get task by ID.
        
        Args:
            task_id: Task ID (composite format: provider_id:task_id)
            
        Returns:
            Task details
        """
        return await self._request("GET", f"/api/v1/tasks/{task_id}")
    
    async def create_task(
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
        """
        Create a new task.
        
        Args:
            project_id: Project ID (composite format)
            title: Task title
            description: Task description
            assignee_id: Assignee user ID
            sprint_id: Sprint ID
            story_points: Story points
            priority: Priority level
            task_type: Task type
            parent_id: Parent task ID
            
        Returns:
            Created task
        """
        data = {
            "project_id": project_id,
            "title": title
        }
        if description:
            data["description"] = description
        if assignee_id:
            data["assignee_id"] = assignee_id
        if sprint_id:
            data["sprint_id"] = sprint_id
        if story_points is not None:
            data["story_points"] = story_points
        if priority:
            data["priority"] = priority
        if task_type:
            data["task_type"] = task_type
        if parent_id:
            data["parent_id"] = parent_id
        
        return await self._request("POST", "/api/v1/tasks", json=data)
    
    async def update_task(
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
        """
        Update a task.
        
        Args:
            task_id: Task ID (composite format)
            title: New title
            description: New description
            status: New status
            assignee_id: New assignee
            sprint_id: New sprint
            story_points: New story points
            priority: New priority
            progress: Progress percentage (0-100)
            
        Returns:
            Updated task
        """
        data = {}
        if title is not None:
            data["title"] = title
        if description is not None:
            data["description"] = description
        if status is not None:
            data["status"] = status
        if assignee_id is not None:
            data["assignee_id"] = assignee_id
        if sprint_id is not None:
            data["sprint_id"] = sprint_id
        if story_points is not None:
            data["story_points"] = story_points
        if priority is not None:
            data["priority"] = priority
        if progress is not None:
            data["progress"] = progress
        
        return await self._request("PUT", f"/api/v1/tasks/{task_id}", json=data)
    
    # ==================== Sprints ====================
    
    async def list_sprints(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> dict[str, Any]:
        """
        List ALL sprints.
        
        Automatically paginates to fetch all sprints.
        
        Args:
            project_id: Filter by project ID
            status: Filter by status (active, closed, future)
            
        Returns:
            ListResponse with ALL sprints
        """
        params = {}
        if project_id:
            params["project_id"] = project_id
        if status:
            params["status"] = status
        
        return await self._paginate_all("/api/v1/sprints", params=params)
    
    async def get_sprint(self, sprint_id: str) -> dict[str, Any]:
        """
        Get sprint by ID.
        
        Args:
            sprint_id: Sprint ID (composite format)
            
        Returns:
            Sprint details
        """
        return await self._request("GET", f"/api/v1/sprints/{sprint_id}")
    
    async def get_sprint_tasks(
        self,
        sprint_id: str,
        limit: int = 100
    ) -> dict[str, Any]:
        """
        Get tasks in a sprint.
        
        Args:
            sprint_id: Sprint ID
            limit: Maximum results
            
        Returns:
            ListResponse with tasks
        """
        params = {"limit": limit}
        return await self._request("GET", f"/api/v1/sprints/{sprint_id}/tasks", params=params)
    
    # ==================== Users ====================
    
    async def list_users(
        self,
        project_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        List ALL users.
        
        Automatically paginates to fetch all users.
        
        Args:
            project_id: Filter by project ID
            
        Returns:
            ListResponse with ALL users
        """
        params = {}
        if project_id:
            params["project_id"] = project_id
        
        return await self._paginate_all("/api/v1/users", params=params)
    
    async def get_user(self, user_id: str) -> dict[str, Any]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID (composite format)
            
        Returns:
            User details
        """
        return await self._request("GET", f"/api/v1/users/{user_id}")
    
    # ==================== Providers ====================
    
    async def list_providers(self) -> dict[str, Any]:
        """
        List ALL configured providers.
        
        Automatically paginates to fetch all providers.
        
        Returns:
            ListResponse with ALL providers
        """
        return await self._paginate_all("/api/v1/providers")
    
    async def get_provider(self, provider_id: str) -> dict[str, Any]:
        """
        Get provider by ID.
        
        Args:
            provider_id: Provider ID
            
        Returns:
            Provider details
        """
        return await self._request("GET", f"/api/v1/providers/{provider_id}")
    
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
        """
        Sync provider configuration from backend.
        
        Args:
            backend_provider_id: Backend provider ID
            provider_type: Provider type
            name: Provider name
            base_url: Provider base URL
            api_key: API key
            api_token: API token
            username: Username
            is_active: Is provider active
            additional_config: Additional configuration
            
        Returns:
            Sync result
        """
        data = {
            "backend_provider_id": backend_provider_id,
            "provider_type": provider_type,
            "name": name,
            "base_url": base_url,
            "is_active": is_active
        }
        if api_key:
            data["api_key"] = api_key
        if api_token:
            data["api_token"] = api_token
        if username:
            data["username"] = username
        if additional_config:
            data["additional_config"] = additional_config
        
        return await self._request("POST", "/api/v1/providers/sync", json=data)
    
    async def delete_provider(self, provider_id: str) -> dict[str, Any]:
        """
        Delete a provider.
        
        Args:
            provider_id: Provider ID
            
        Returns:
            Delete result
        """
        return await self._request("DELETE", f"/api/v1/providers/{provider_id}")
    
    # ==================== Epics ====================
    
    async def list_epics(
        self,
        project_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        List ALL epics.
        
        Automatically paginates to fetch all epics.
        
        Args:
            project_id: Filter by project ID
            
        Returns:
            ListResponse with ALL epics
        """
        params = {}
        if project_id:
            params["project_id"] = project_id
        
        return await self._paginate_all("/api/v1/epics", params=params)
    
    async def get_epic(self, epic_id: str) -> dict[str, Any]:
        """
        Get epic by ID.
        
        Args:
            epic_id: Epic ID (composite format)
            
        Returns:
            Epic details
        """
        return await self._request("GET", f"/api/v1/epics/{epic_id}")
    
    async def create_epic(
        self,
        project_id: str,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Create an epic.
        
        Args:
            project_id: Project ID
            name: Epic name
            description: Epic description
            color: Epic color
            
        Returns:
            Created epic
        """
        data = {
            "project_id": project_id,
            "name": name
        }
        if description:
            data["description"] = description
        if color:
            data["color"] = color
        
        return await self._request("POST", "/api/v1/epics", json=data)
    
    async def update_epic(
        self,
        epic_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        Update an epic.
        
        Args:
            epic_id: Epic ID
            name: New name
            description: New description
            color: New color
            
        Returns:
            Updated epic
        """
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if color is not None:
            data["color"] = color
        # Include any additional kwargs
        data.update(kwargs)
        
        return await self._request("PUT", f"/api/v1/epics/{epic_id}", json=data)
    
    async def delete_epic(self, epic_id: str) -> dict[str, Any]:
        """
        Delete an epic.
        
        Args:
            epic_id: Epic ID
            
        Returns:
            Delete result
        """
        return await self._request("DELETE", f"/api/v1/epics/{epic_id}")
    
    # ==================== Statuses & Priorities ====================
    
    async def list_statuses(
        self,
        project_id: str,
        entity_type: str = "task"
    ) -> dict[str, Any]:
        """
        List available statuses for a project.
        
        Args:
            project_id: Project ID
            entity_type: Entity type (task, sprint, etc.)
            
        Returns:
            ListResponse with statuses
        """
        params = {"entity_type": entity_type}
        return await self._request("GET", f"/api/v1/projects/{project_id}/statuses", params=params)
    
    async def list_priorities(
        self,
        project_id: str
    ) -> dict[str, Any]:
        """
        List available priorities for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            ListResponse with priorities
        """
        return await self._request("GET", f"/api/v1/projects/{project_id}/priorities")


# Singleton instance for convenience
_default_client: Optional[AsyncPMServiceClient] = None


def get_pm_service_client(base_url: Optional[str] = None) -> AsyncPMServiceClient:
    """
    Get PM Service client instance.
    
    Args:
        base_url: Optional custom base URL
        
    Returns:
        AsyncPMServiceClient instance
    """
    global _default_client
    
    if base_url:
        return AsyncPMServiceClient(base_url=base_url)
    
    if _default_client is None:
        _default_client = AsyncPMServiceClient()
    
    return _default_client

