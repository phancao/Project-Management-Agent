# PM Service Handler
"""
Unified PM Handler for PM Service.
This is the single source of truth for PM provider interactions.
"""

import logging
from datetime import date
from typing import Any, Optional

from sqlalchemy.orm import Session

from pm_service.database.models import PMProviderConnection
from pm_service.providers.factory import create_pm_provider
from pm_service.providers.base import BasePMProvider
from pm_service.providers.models import PMTask, PMProject, PMSprint

logger = logging.getLogger(__name__)


class PMHandler:
    """
    Unified PM Handler for all PM provider interactions.
    
    This handler is used by both:
    - PM Service API endpoints
    - Client libraries (Backend API, MCP Server)
    """
    
    def __init__(
        self,
        db_session: Session,
        user_id: Optional[str] = None
    ):
        """
        Initialize PM Handler.
        
        Args:
            db_session: Database session for querying providers
            user_id: Optional user ID to filter providers
        """
        self.db = db_session
        self.user_id = user_id
        self._provider_cache: dict[str, BasePMProvider] = {}
        self._errors: list[dict[str, Any]] = []
    
    # ==================== Provider Management ====================
    
    def get_active_providers(self) -> list[PMProviderConnection]:
        """Get all active PM providers."""
        query = self.db.query(PMProviderConnection).filter(
            PMProviderConnection.is_active.is_(True)
        )
        
        if self.user_id:
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    PMProviderConnection.created_by == self.user_id,
                    PMProviderConnection.created_by.is_(None)
                )
            )
        
        return query.all()
    
    def get_provider_by_id(self, provider_id: str) -> Optional[PMProviderConnection]:
        """Get provider by ID (PM Service ID or backend_provider_id)."""
        from uuid import UUID
        
        # First try to find by PM Service ID
        provider = self.db.query(PMProviderConnection).filter(
            PMProviderConnection.id == provider_id
        ).first()
        
        if provider:
            return provider
        
        # If not found, try to find by backend_provider_id
        try:
            backend_uuid = UUID(provider_id)
            provider = self.db.query(PMProviderConnection).filter(
                PMProviderConnection.backend_provider_id == backend_uuid
            ).first()
        except (ValueError, TypeError):
            # provider_id is not a valid UUID, skip backend_provider_id lookup
            pass
        
        return provider
    
    def create_provider_instance(self, provider_conn: PMProviderConnection) -> BasePMProvider:
        """Create provider instance from connection config."""
        cache_key = str(provider_conn.id)
        
        if cache_key in self._provider_cache:
            return self._provider_cache[cache_key]
        
        config = provider_conn.get_provider_config()
        provider = create_pm_provider(**config)
        self._provider_cache[cache_key] = provider
        
        return provider
    
    def get_provider(self, provider_id: str) -> Optional[BasePMProvider]:
        """Get provider instance by ID."""
        provider_conn = self.get_provider_by_id(provider_id)
        if not provider_conn:
            return None
        return self.create_provider_instance(provider_conn)
    
    def record_error(self, provider_id: str, error: Exception) -> None:
        """Record provider error."""
        self._errors.append({
            "provider_id": provider_id,
            "error": str(error),
            "type": type(error).__name__
        })
        logger.error(f"Provider {provider_id} error: {error}")
    
    def get_errors(self) -> list[dict[str, Any]]:
        """Get recorded errors."""
        return self._errors.copy()
    
    def clear_errors(self) -> None:
        """Clear recorded errors."""
        self._errors.clear()
    
    # ==================== Projects ====================
    
    async def list_projects(
        self,
        provider_id: Optional[str] = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """List projects from all or specific provider."""
        projects = []
        
        if provider_id:
            providers = [self.get_provider_by_id(provider_id)]
            providers = [p for p in providers if p]
        else:
            providers = self.get_active_providers()
        
        for provider_conn in providers:
            try:
                provider = self.create_provider_instance(provider_conn)
                provider_projects = await provider.list_projects()
                
                for project in provider_projects[:limit]:
                    project_dict = self._to_dict(project)
                    # Format project ID as composite: provider_id:project_id
                    # Use backend_provider_id if available (for frontend compatibility),
                    # otherwise use PM Service provider ID
                    original_id = str(project_dict.get("id", ""))
                    if ":" not in original_id:
                        # Prefer backend_provider_id for frontend compatibility
                        provider_id_for_project = (
                            str(provider_conn.backend_provider_id) 
                            if hasattr(provider_conn, 'backend_provider_id') and provider_conn.backend_provider_id
                            else str(provider_conn.id)
                        )
                        project_dict["id"] = f"{provider_id_for_project}:{original_id}"
                    # Store both provider IDs for reference
                    project_dict["provider_id"] = str(provider_conn.id)
                    if hasattr(provider_conn, 'backend_provider_id') and provider_conn.backend_provider_id:
                        project_dict["backend_provider_id"] = str(provider_conn.backend_provider_id)
                    project_dict["provider_name"] = provider_conn.name
                    # Ensure status is always a string (not null)
                    if project_dict.get("status") is None:
                        project_dict["status"] = "None"
                    projects.append(project_dict)
                    
            except Exception as e:
                self.record_error(str(provider_conn.id), e)
                continue
        
        return projects[:limit]
    
    async def get_project(self, project_id: str) -> Optional[dict[str, Any]]:
        """Get project by ID."""
        provider_id, actual_id = self._parse_composite_id(project_id)
        
        if provider_id:
            provider_conn = self.get_provider_by_id(provider_id)
            if provider_conn:
                try:
                    provider = self.create_provider_instance(provider_conn)
                    project = await provider.get_project(actual_id)
                    if project:
                        project_dict = self._to_dict(project)
                        project_dict["provider_id"] = str(provider_conn.id)
                        project_dict["provider_name"] = provider_conn.name
                        return project_dict
                except Exception as e:
                    self.record_error(provider_id, e)
        
        # Search all providers
        for provider_conn in self.get_active_providers():
            try:
                provider = self.create_provider_instance(provider_conn)
                project = await provider.get_project(actual_id)
                if project:
                    project_dict = self._to_dict(project)
                    project_dict["provider_id"] = str(provider_conn.id)
                    project_dict["provider_name"] = provider_conn.name
                    return project_dict
            except Exception as e:
                continue
        
        return None
    
    # ==================== Tasks ====================
    
    async def list_tasks(
        self,
        project_id: Optional[str] = None,
        sprint_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        List tasks with filters.
        
        Note: This method returns ALL matching tasks from providers.
        Pagination/limiting should be handled by the API router layer.
        The providers already handle their own pagination to fetch all data.
        """
        tasks = []
        
        # Parse project_id if provided
        provider_id = None
        actual_project_id = None
        if project_id:
            provider_id, actual_project_id = self._parse_composite_id(project_id)
        
        # Parse sprint_id
        actual_sprint_id = None
        if sprint_id:
            _, actual_sprint_id = self._parse_composite_id(sprint_id)
        
        if provider_id:
            providers = [self.get_provider_by_id(provider_id)]
            providers = [p for p in providers if p]
        else:
            providers = self.get_active_providers()
        
        for provider_conn in providers:
            try:
                provider = self.create_provider_instance(provider_conn)
                provider_tasks = await provider.list_tasks(
                    project_id=actual_project_id,
                    assignee_id=assignee_id
                )
                
                # Filter by sprint if provided
                if actual_sprint_id:
                    provider_tasks = [
                        t for t in provider_tasks
                        if self._task_in_sprint(t, actual_sprint_id)
                    ]
                
                for task in provider_tasks:
                    task_dict = self._to_dict(task)
                    task_dict["provider_id"] = str(provider_conn.id)
                    task_dict["provider_name"] = provider_conn.name
                    tasks.append(task_dict)
                    
            except Exception as e:
                self.record_error(str(provider_conn.id), e)
                continue
        
        return tasks
    
    async def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        """Get task by ID."""
        provider_id, actual_id = self._parse_composite_id(task_id)
        
        if provider_id:
            provider_conn = self.get_provider_by_id(provider_id)
            if provider_conn:
                try:
                    provider = self.create_provider_instance(provider_conn)
                    task = await provider.get_task(actual_id)
                    if task:
                        task_dict = self._to_dict(task)
                        task_dict["provider_id"] = str(provider_conn.id)
                        task_dict["provider_name"] = provider_conn.name
                        return task_dict
                except Exception as e:
                    self.record_error(provider_id, e)
        
        return None
    
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
    ) -> Optional[dict[str, Any]]:
        """Create a new task."""
        provider_id, actual_project_id = self._parse_composite_id(project_id)
        
        if not provider_id:
            raise ValueError("project_id must include provider_id (format: provider_id:project_id)")
        
        provider_conn = self.get_provider_by_id(provider_id)
        if not provider_conn:
            raise ValueError(f"Provider {provider_id} not found")
        
        provider = self.create_provider_instance(provider_conn)
        
        # Parse sprint_id if provided
        actual_sprint_id = None
        if sprint_id:
            _, actual_sprint_id = self._parse_composite_id(sprint_id)
        
        task = await provider.create_task(
            project_id=actual_project_id,
            title=title,
            description=description,
            assignee_id=assignee_id,
            sprint_id=actual_sprint_id,
            story_points=story_points,
            priority=priority,
            task_type=task_type,
            parent_id=parent_id
        )
        
        if task:
            task_dict = self._to_dict(task)
            task_dict["provider_id"] = str(provider_conn.id)
            task_dict["provider_name"] = provider_conn.name
            return task_dict
        
        return None
    
    async def update_task(
        self,
        task_id: str,
        **updates
    ) -> Optional[dict[str, Any]]:
        """Update a task."""
        provider_id, actual_id = self._parse_composite_id(task_id)
        
        if not provider_id:
            raise ValueError("task_id must include provider_id")
        
        provider_conn = self.get_provider_by_id(provider_id)
        if not provider_conn:
            raise ValueError(f"Provider {provider_id} not found")
        
        provider = self.create_provider_instance(provider_conn)
        task = await provider.update_task(actual_id, **updates)
        
        if task:
            task_dict = self._to_dict(task)
            task_dict["provider_id"] = str(provider_conn.id)
            task_dict["provider_name"] = provider_conn.name
            return task_dict
        
        return None
    
    # ==================== Sprints ====================
    
    async def list_sprints(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """List sprints."""
        sprints = []
        
        provider_id = None
        actual_project_id = None
        if project_id:
            provider_id, actual_project_id = self._parse_composite_id(project_id)
        
        if provider_id:
            providers = [self.get_provider_by_id(provider_id)]
            providers = [p for p in providers if p]
        else:
            providers = self.get_active_providers()
        
        for provider_conn in providers:
            try:
                provider = self.create_provider_instance(provider_conn)
                provider_sprints = await provider.list_sprints(project_id=actual_project_id)
                
                for sprint in provider_sprints:
                    sprint_dict = self._to_dict(sprint)
                    sprint_dict["provider_id"] = str(provider_conn.id)
                    sprint_dict["provider_name"] = provider_conn.name
                    sprints.append(sprint_dict)
                    
            except Exception as e:
                self.record_error(str(provider_conn.id), e)
                continue
        
        return sprints[:limit]
    
    async def get_sprint(self, sprint_id: str) -> Optional[dict[str, Any]]:
        """Get sprint by ID."""
        provider_id, actual_id = self._parse_composite_id(sprint_id)
        
        if provider_id:
            provider_conn = self.get_provider_by_id(provider_id)
            if provider_conn:
                try:
                    provider = self.create_provider_instance(provider_conn)
                    sprint = await provider.get_sprint(actual_id)
                    if sprint:
                        sprint_dict = self._to_dict(sprint)
                        sprint_dict["provider_id"] = str(provider_conn.id)
                        sprint_dict["provider_name"] = provider_conn.name
                        return sprint_dict
                except Exception as e:
                    self.record_error(provider_id, e)
        
        return None
    
    # ==================== Users ====================
    
    async def list_users(
        self,
        project_id: Optional[str] = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """List users."""
        users = []
        
        provider_id = None
        actual_project_id = None
        if project_id:
            provider_id, actual_project_id = self._parse_composite_id(project_id)
        
        if provider_id:
            providers = [self.get_provider_by_id(provider_id)]
            providers = [p for p in providers if p]
        else:
            providers = self.get_active_providers()
        
        for provider_conn in providers:
            try:
                provider = self.create_provider_instance(provider_conn)
                provider_users = await provider.list_users(project_id=actual_project_id)
                
                for user in provider_users:
                    user_dict = self._to_dict(user)
                    user_dict["provider_id"] = str(provider_conn.id)
                    user_dict["provider_name"] = provider_conn.name
                    users.append(user_dict)
                    
            except Exception as e:
                self.record_error(str(provider_conn.id), e)
                continue
        
        return users[:limit]
    
    async def get_user(self, user_id: str) -> Optional[dict[str, Any]]:
        """Get user by ID."""
        provider_id, actual_id = self._parse_composite_id(user_id)
        
        if provider_id:
            provider_conn = self.get_provider_by_id(provider_id)
            if provider_conn:
                try:
                    provider = self.create_provider_instance(provider_conn)
                    user = await provider.get_user(actual_id)
                    if user:
                        user_dict = self._to_dict(user)
                        user_dict["provider_id"] = str(provider_conn.id)
                        user_dict["provider_name"] = provider_conn.name
                        return user_dict
                except Exception as e:
                    self.record_error(provider_id, e)
        
        return None
    
    # ==================== Epics ====================
    
    async def list_epics(
        self,
        project_id: Optional[str] = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """List epics."""
        epics = []
        
        provider_id = None
        actual_project_id = None
        if project_id:
            provider_id, actual_project_id = self._parse_composite_id(project_id)
        
        if provider_id:
            providers = [self.get_provider_by_id(provider_id)]
            providers = [p for p in providers if p]
        else:
            providers = self.get_active_providers()
        
        for provider_conn in providers:
            try:
                provider = self.create_provider_instance(provider_conn)
                if hasattr(provider, 'list_epics'):
                    provider_epics = await provider.list_epics(project_id=actual_project_id)
                    
                    for epic in provider_epics:
                        epic_dict = self._to_dict(epic)
                        epic_dict["provider_id"] = str(provider_conn.id)
                        epic_dict["provider_name"] = provider_conn.name
                        epics.append(epic_dict)
                        
            except Exception as e:
                self.record_error(str(provider_conn.id), e)
                continue
        
        return epics[:limit]
    
    async def get_epic(self, epic_id: str) -> Optional[dict[str, Any]]:
        """Get epic by ID."""
        provider_id, actual_id = self._parse_composite_id(epic_id)
        
        if provider_id:
            provider_conn = self.get_provider_by_id(provider_id)
            if provider_conn:
                try:
                    provider = self.create_provider_instance(provider_conn)
                    if hasattr(provider, 'get_epic'):
                        epic = await provider.get_epic(actual_id)
                        if epic:
                            epic_dict = self._to_dict(epic)
                            epic_dict["provider_id"] = str(provider_conn.id)
                            epic_dict["provider_name"] = provider_conn.name
                            return epic_dict
                except Exception as e:
                    self.record_error(provider_id, e)
        
        return None
    
    async def create_epic(
        self,
        project_id: str,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """Create a new epic."""
        provider_id, actual_project_id = self._parse_composite_id(project_id)
        
        if not provider_id:
            raise ValueError("project_id must include provider_id (format: provider_id:project_id)")
        
        provider_conn = self.get_provider_by_id(provider_id)
        if not provider_conn:
            raise ValueError(f"Provider {provider_id} not found")
        
        provider = self.create_provider_instance(provider_conn)
        
        if not hasattr(provider, 'create_epic'):
            raise ValueError(f"Provider {provider_conn.provider_type} does not support epics")
        
        epic = await provider.create_epic(
            project_id=actual_project_id,
            name=name,
            description=description,
            color=color
        )
        
        if epic:
            epic_dict = self._to_dict(epic)
            epic_dict["provider_id"] = str(provider_conn.id)
            epic_dict["provider_name"] = provider_conn.name
            return epic_dict
        
        return None
    
    async def update_epic(
        self,
        epic_id: str,
        **updates
    ) -> Optional[dict[str, Any]]:
        """Update an epic."""
        provider_id, actual_id = self._parse_composite_id(epic_id)
        
        if not provider_id:
            raise ValueError("epic_id must include provider_id")
        
        provider_conn = self.get_provider_by_id(provider_id)
        if not provider_conn:
            raise ValueError(f"Provider {provider_id} not found")
        
        provider = self.create_provider_instance(provider_conn)
        
        if not hasattr(provider, 'update_epic'):
            raise ValueError(f"Provider {provider_conn.provider_type} does not support epic updates")
        
        epic = await provider.update_epic(actual_id, **updates)
        
        if epic:
            epic_dict = self._to_dict(epic)
            epic_dict["provider_id"] = str(provider_conn.id)
            epic_dict["provider_name"] = provider_conn.name
            return epic_dict
        
        return None
    
    async def delete_epic(self, epic_id: str) -> bool:
        """Delete an epic."""
        provider_id, actual_id = self._parse_composite_id(epic_id)
        
        if not provider_id:
            raise ValueError("epic_id must include provider_id")
        
        provider_conn = self.get_provider_by_id(provider_id)
        if not provider_conn:
            raise ValueError(f"Provider {provider_id} not found")
        
        provider = self.create_provider_instance(provider_conn)
        
        if not hasattr(provider, 'delete_epic'):
            raise ValueError(f"Provider {provider_conn.provider_type} does not support epic deletion")
        
        return await provider.delete_epic(actual_id)
    
    # ==================== Helper Methods ====================
    
    def _parse_composite_id(self, composite_id: str) -> tuple[Optional[str], str]:
        """Parse composite ID (provider_id:actual_id) into parts."""
        if ":" in composite_id:
            parts = composite_id.split(":", 1)
            return parts[0], parts[1]
        return None, composite_id
    
    def _to_dict(self, obj: Any) -> dict[str, Any]:
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
    
    def _task_in_sprint(self, task: Any, sprint_id: str) -> bool:
        """Check if task belongs to sprint."""
        task_dict = self._to_dict(task) if not isinstance(task, dict) else task
        
        task_sprint = task_dict.get("sprint_id") or task_dict.get("version_id") or task_dict.get("version")
        if task_sprint:
            if isinstance(task_sprint, dict):
                task_sprint_id = str(task_sprint.get("id", ""))
            else:
                task_sprint_id = str(task_sprint)
            
            if ":" in task_sprint_id:
                task_sprint_id = task_sprint_id.split(":", 1)[1]
            
            return task_sprint_id == sprint_id
        
        return False

