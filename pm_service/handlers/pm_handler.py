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
    
    def get_pm_service_url(self) -> str:
        """
        Get PM Service URL from provider configuration.
        Checks additional_config of active providers for 'pm_service_url'.
        
        Raises:
            ValueError: If no active provider has pm_service_url configured
        """
        providers = self.get_active_providers()
        
        if not providers:
            raise ValueError(
                "No active PM providers configured. "
                "Please add at least one PM provider with pm_service_url in additional_config."
            )
        
        for provider in providers:
            if provider.additional_config and isinstance(provider.additional_config, dict):
                pm_service_url = provider.additional_config.get("pm_service_url")
                if pm_service_url:
                    logger.info(f"Found PM Service URL from provider {provider.id}: {pm_service_url}")
                    return pm_service_url
        
        # No provider has pm_service_url configured
        provider_names = [p.name for p in providers]
        raise ValueError(
            f"No PM provider has 'pm_service_url' configured in additional_config. "
            f"Active providers: {', '.join(provider_names)}. "
            "Please add 'pm_service_url' to at least one provider's additional_config."
        )
    
    def get_provider_by_id(self, provider_id: str, require_active: bool = True) -> Optional[PMProviderConnection]:
        """Get provider by ID (PM Service ID or backend_provider_id).
        
        Args:
            provider_id: The provider ID to look up
            require_active: If True, raise error if provider is disabled (default: True)
            
        Returns:
            PMProviderConnection if found
            
        Raises:
            ValueError: If provider is found but is disabled and require_active=True
        """
        from uuid import UUID
        
        provider = None
        
        # First try to find by PM Service ID
        provider = self.db.query(PMProviderConnection).filter(
            PMProviderConnection.id == provider_id
        ).first()
        
        if not provider:
            # If not found, try to find by backend_provider_id
            try:
                backend_uuid = UUID(provider_id)
                provider = self.db.query(PMProviderConnection).filter(
                    PMProviderConnection.backend_provider_id == backend_uuid
                ).first()
            except (ValueError, TypeError):
                # provider_id is not a valid UUID, skip backend_provider_id lookup
                pass
        
        # Check if provider is active when required
        if provider and require_active and not provider.is_active:
            provider_name = provider.name or f"ID:{provider_id}"
            logger.warning(f"Attempted to use disabled provider: {provider_name}")
            raise ValueError(f"Provider '{provider_name}' is disabled. Please enable it or select a different project.")
        
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
        """Record provider error. Connection errors are logged as warnings (expected behavior)."""
        self._errors.append({
            "provider_id": provider_id,
            "error": str(error),
            "type": type(error).__name__
        })
        # Connection errors are expected when providers are unavailable - use WARNING
        error_type = type(error).__name__
        error_str = str(error)
        is_connection_error = (
            "ConnectionError" in error_type or 
            "MaxRetryError" in error_type or
            "NameResolutionError" in error_str or
            "Failed to resolve" in error_str or
            "Connection refused" in error_str or
            "timeout" in error_str.lower()
        )
        if is_connection_error:
            logger.warning(f"Provider {provider_id} unavailable: {error}")
        else:
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
        user_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        List projects from all or specific provider.
        Uses DataBuffer for streaming and OOM safety.
        """
        import time
        from ..utils.data_buffer import DataBuffer, ensure_async_iterator
        
        run_id = f"run_{int(time.time())}"
        logger.info(f"[PM-DEBUG][{run_id}] list_projects START: provider_id={provider_id}, user_id={user_id}")
        
        buffer = DataBuffer(prefix="projects_")
        
        if provider_id:
            providers = [self.get_provider_by_id(provider_id)]
            providers = [p for p in providers if p]
        else:
            providers = self.get_active_providers()
        
        for provider_conn in providers:
            try:
                # Handle user_id for specific provider if it's a composite ID
                actual_user_id = user_id
                if user_id and ":" in user_id:
                    p_id, u_id = self._parse_composite_id(user_id)
                    if p_id == str(provider_conn.id) or p_id == str(provider_conn.backend_provider_id):
                        actual_user_id = u_id
                    else:
                        if p_id: 
                            continue 
                
                provider = self.create_provider_instance(provider_conn)
                if not hasattr(provider, 'list_projects'):
                    continue

                logger.info(f"[PM-DEBUG][{run_id}] Streaming projects from {provider_conn.name} (ID: {provider_conn.id})...")
                start = time.time()
                
                # Get the iterator (might be list or async iterator)
                raw_result = provider.list_projects(user_id=actual_user_id)
                
                # Define enrichment generator
                async def enriched_iterator():
                    async for project in ensure_async_iterator(raw_result):
                        try:
                            project_dict = self._to_dict(project)
                            original_id = str(project_dict.get("id", ""))
                            if ":" not in original_id:
                                provider_id_for_project = (
                                    str(provider_conn.backend_provider_id) 
                                    if hasattr(provider_conn, 'backend_provider_id') and provider_conn.backend_provider_id
                                    else str(provider_conn.id)
                                )
                                project_dict["id"] = f"{provider_id_for_project}:{original_id}"
                            
                            project_dict["provider_id"] = str(provider_conn.id)
                            if hasattr(provider_conn, 'backend_provider_id') and provider_conn.backend_provider_id:
                                project_dict["backend_provider_id"] = str(provider_conn.backend_provider_id)
                            project_dict["provider_name"] = provider_conn.name
                            if project_dict.get("status") is None:
                                project_dict["status"] = "None"
                            yield project_dict
                        except Exception as e:
                            logger.error(f"Error enriching project from {provider_conn.name}: {e}")

                count = await buffer.write_items(enriched_iterator())
                dur = time.time() - start
                logger.info(f"[PM-DEBUG][{run_id}] Streamed {count} projects from {provider_conn.name} in {dur:.3f}s")
                    
            except Exception as e:
                self.record_error(str(provider_conn.id), e)
                logger.warning(f"[PM-DEBUG][{run_id}] Provider {provider_conn.name} unavailable, skipping: {type(e).__name__}")
                continue

        projects = await buffer.read_all()
        buffer.cleanup()
        logger.info(f"[PM-DEBUG][{run_id}] list_projects END: Total projects={len(projects)}")
        return projects
    
    async def get_project(self, project_id: str) -> Optional[dict[str, Any]]:
        """Get project by ID. Returns project with composite ID (provider:shortId) for multi-provider safety."""
        provider_id, actual_id = self._parse_composite_id(project_id)
        
        def _wrap_composite_id(entity_dict: dict, provider_conn) -> dict:
            """Helper to wrap entity ID with provider prefix."""
            provider_id_prefix = (
                str(provider_conn.backend_provider_id) 
                if hasattr(provider_conn, 'backend_provider_id') and provider_conn.backend_provider_id
                else str(provider_conn.id)
            )
            original_id = str(entity_dict.get("id", ""))
            if ":" not in original_id:
                entity_dict["id"] = f"{provider_id_prefix}:{original_id}"
            entity_dict["provider_id"] = str(provider_conn.id)
            entity_dict["provider_name"] = provider_conn.name
            return entity_dict
        
        if provider_id:
            provider_conn = self.get_provider_by_id(provider_id)
            if provider_conn:
                try:
                    provider = self.create_provider_instance(provider_conn)
                    project = await provider.get_project(actual_id)
                    if project:
                        project_dict = self._to_dict(project)
                        return _wrap_composite_id(project_dict, provider_conn)
                except Exception as e:
                    self.record_error(provider_id, e)
        
        # Search all providers
        for provider_conn in self.get_active_providers():
            try:
                provider = self.create_provider_instance(provider_conn)
                project = await provider.get_project(actual_id)
                if project:
                    project_dict = self._to_dict(project)
                    return _wrap_composite_id(project_dict, provider_conn)
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

        provider_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        List tasks with filters.
        
        Note: This method returns ALL matching tasks from providers.
        Pagination/limiting should be handled by the API router layer.
        The providers already handle their own pagination to fetch all data.
        """
        import datetime
        import logging
        import asyncio
        import time
        
        run_id = f"run_{int(time.time())}"
        logger.info(f"[PM-DEBUG][{run_id}] list_tasks START: project_id={project_id}, sprint_id={sprint_id}")

        tasks = []
        
        # Parse project_id if provided
        provider_id_from_project = None
        actual_project_id = None
        if project_id:
            provider_id_from_project, actual_project_id = self._parse_composite_id(project_id)
        
        # Parse sprint_id
        actual_sprint_id = None
        if sprint_id:
            _, actual_sprint_id = self._parse_composite_id(sprint_id)
        
        # Determine providers to fetch from
        providers = []
        target_provider_id = provider_id or provider_id_from_project
        
        if target_provider_id:
            # Fetch from specific provider
            p_conn = self.get_provider_by_id(target_provider_id)
            if p_conn:
                providers = [p_conn]
        else:
            # Fetch from all active providers
            providers = self.get_active_providers()
        
        # Prepare fetch tasks
        # Refactored to use DataBuffer and sequential processing to prevent OOM
        # and ensure reliable streaming to disk.
        
        from ..utils.data_buffer import DataBuffer, ensure_async_iterator
        buffer = DataBuffer(prefix="tasks_")
        
        provider_map = [] # To keep track of successful providers if needed
        
        for provider_conn in providers:
            try:
                # Handle user_id for specific provider if it's a composite ID
                # (Logic from list_projects preserved roughly, though list_tasks uses project_id/sprint_id mainly)
                
                provider = self.create_provider_instance(provider_conn)
                p_id = str(provider_conn.id)
                
                # Determine sprint_id for this provider
                s_id = None
                if sprint_id:
                     if ":" in sprint_id:
                         sp_pid, sp_sid = self._parse_composite_id(sprint_id)
                         if sp_pid == p_id:
                             s_id = sp_sid
                     else:
                         s_id = sprint_id
                
                p_project_id = actual_project_id
                
                # Check if we should skip this provider (if project_id was specific to another provider)
                # target_provider_id logic handles this implicitly by filtering `providers` list
                
                if hasattr(provider, 'list_tasks'):
                    logger.info(f"[PM-DEBUG][{run_id}] Streaming tasks from {provider_conn.name}...")
                    
                    # Async iterator call or list (handled by ensure_async_iterator)
                    raw_result = provider.list_tasks(
                        project_id=p_project_id,
                        assignee_id=assignee_id,
                        sprint_id=s_id,
                        status=status  # Pass status filter to provider
                    )
                    
                    # Wrapper to inject provider info and filter by sprint
                    async def enriched_iterator():
                        async for task in ensure_async_iterator(raw_result):
                            # Apply sprint filter if needed (double check)
                            if s_id and not self._task_in_sprint(task, s_id):
                                continue
                                
                            task_dict = self._to_dict(task)
                            
                            # Normalize IDs with provider prefix
                            provider_id_prefix = (
                                str(provider_conn.backend_provider_id) 
                                if hasattr(provider_conn, 'backend_provider_id') and provider_conn.backend_provider_id
                                else str(provider_conn.id)
                            )
                            
                            # Normalize Task ID
                            original_id = str(task_dict.get("id", ""))
                            if ":" not in original_id:
                                task_dict["id"] = f"{provider_id_prefix}:{original_id}"
                                
                            # Normalize References
                            # This ensures that references like sprint_id match the composite IDs used by list_sprints
                            for field in ["sprint_id", "project_id", "assignee_id", "parent_id", "epic_id"]:
                                ref_id = task_dict.get(field)
                                if ref_id and ":" not in str(ref_id):
                                    task_dict[field] = f"{provider_id_prefix}:{ref_id}"

                            task_dict["provider_id"] = str(provider_conn.id)
                            task_dict["provider_name"] = provider_conn.name
                            yield task_dict
                    
                    # Write to buffer
                    count = await buffer.write_items(enriched_iterator())
                    logger.info(f"[PM-DEBUG][{run_id}] Streamed {count} tasks from {provider_conn.name}")
                    
            except Exception as e:
                self.record_error(str(provider_conn.id), e)
                logger.error(f"[PM-DEBUG][{run_id}] Error streaming from {provider_conn.name}: {e}")
                if target_provider_id:
                    raise e
                continue

        # Read all items from buffer to return list
        # This brings items back into memory, but as simple dicts, and only for the final response.
        # Ideally we would stream this too, but Router expects list.
        # This prevents the accumulation of Pydantic models and Response objects during fetch.
        tasks = await buffer.read_all()
        buffer.cleanup()

        logger.info(f"[PM-DEBUG][{run_id}] list_tasks END: Total tasks={len(tasks)}")
        return tasks
    
    async def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        """Get task by ID. Returns task with composite ID (provider:shortId) for multi-provider safety."""
        provider_id, actual_id = self._parse_composite_id(task_id)
        
        if provider_id:
            provider_conn = self.get_provider_by_id(provider_id)
            if provider_conn:
                try:
                    provider = self.create_provider_instance(provider_conn)
                    task = await provider.get_task(actual_id)
                    if task:
                        task_dict = self._to_dict(task)
                        # Ensure ID is composite for multi-provider safety
                        provider_id_prefix = (
                            str(provider_conn.backend_provider_id) 
                            if hasattr(provider_conn, 'backend_provider_id') and provider_conn.backend_provider_id
                            else str(provider_conn.id)
                        )
                        original_id = str(task_dict.get("id", ""))
                        if ":" not in original_id:
                            task_dict["id"] = f"{provider_id_prefix}:{original_id}"
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
            # Ensure ID is composite for multi-provider safety
            provider_id_prefix = (
                str(provider_conn.backend_provider_id) 
                if hasattr(provider_conn, 'backend_provider_id') and provider_conn.backend_provider_id
                else str(provider_conn.id)
            )
            original_id = str(task_dict.get("id", ""))
            if ":" not in original_id:
                task_dict["id"] = f"{provider_id_prefix}:{original_id}"
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
            # Ensure ID is composite for multi-provider safety
            provider_id_prefix = (
                str(provider_conn.backend_provider_id) 
                if hasattr(provider_conn, 'backend_provider_id') and provider_conn.backend_provider_id
                else str(provider_conn.id)
            )
            original_id = str(task_dict.get("id", ""))
            if ":" not in original_id:
                task_dict["id"] = f"{provider_id_prefix}:{original_id}"
            task_dict["provider_id"] = str(provider_conn.id)
            task_dict["provider_name"] = provider_conn.name
            return task_dict
        
        return None
    
    # ==================== Sprints ====================
    
    async def list_sprints(
        self,
        project_id: Optional[str] = None,
        state: Optional[str] = None,
        provider_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """List sprints from providers (streaming)."""
        import time
        from ..utils.data_buffer import DataBuffer, ensure_async_iterator
        
        run_id = f"run_{int(time.time())}"
        logger.info(f"[PM-DEBUG][{run_id}] list_sprints START: project_id={project_id}")
        
        buffer = DataBuffer(prefix="sprints_")
        
        provider_id_arg = provider_id
        actual_project_id = None
        if project_id and ":" in project_id:
             p_id, p_key = self._parse_composite_id(project_id)
             if p_id: 
                 provider_id_arg = p_id
                 actual_project_id = p_key
        elif project_id:
             actual_project_id = project_id

        if provider_id_arg:
            providers = [self.get_provider_by_id(provider_id_arg)]
            providers = [p for p in providers if p]
        else:
            providers = self.get_active_providers()
            
        for provider_conn in providers:
            try:
                # If we have a project_id filter but the provider doesn't match the prefix (if we knew it)
                # But here we rely on provider_id extraction which already filtered the list of providers.
                
                provider = self.create_provider_instance(provider_conn)
                if not hasattr(provider, 'list_sprints'):
                    continue

                logger.info(f"[PM-DEBUG][{run_id}] Streaming sprints from {provider_conn.name}...")
                
                # Pass state only if provider supports it (base method does)
                # But we should check signature? BasePMProvider has it.
                
                raw_result = provider.list_sprints(project_id=actual_project_id, state=state)

                async def enriched_iterator():
                    async for sprint in ensure_async_iterator(raw_result):
                         try:
                             s_dict = self._to_dict(sprint)
                             # Enrich ID
                             original_id = str(s_dict.get("id", ""))
                             if ":" not in original_id:
                                 provider_id_prefix = (
                                     str(provider_conn.backend_provider_id) 
                                     if hasattr(provider_conn, 'backend_provider_id') and provider_conn.backend_provider_id
                                     else str(provider_conn.id)
                                 )
                                 s_dict["id"] = f"{provider_id_prefix}:{original_id}"
                             
                             s_dict["provider_id"] = str(provider_conn.id)
                             s_dict["provider_name"] = provider_conn.name
                             yield s_dict
                         except Exception as e:
                             logger.error(f"Error enriching sprint: {e}")

                await buffer.write_items(enriched_iterator())

            except Exception as e:
                logger.error(f"Error fetching sprints from {provider_conn.name}: {e}")
                self.record_error(str(provider_conn.id), e)
                
        sprints = await buffer.read_all()
        buffer.cleanup()
        logger.info(f"[PM-DEBUG][{run_id}] list_sprints END: Total sprints={len(sprints)}")
        return sprints
    
    async def get_sprint(self, sprint_id: str) -> Optional[dict[str, Any]]:
        """Get sprint by ID. Returns sprint with composite ID (provider:shortId) for multi-provider safety."""
        provider_id, actual_id = self._parse_composite_id(sprint_id)
        
        def _wrap_composite_id(entity_dict: dict, provider_conn) -> dict:
            """Helper to wrap entity ID with provider prefix."""
            provider_id_prefix = (
                str(provider_conn.backend_provider_id) 
                if hasattr(provider_conn, 'backend_provider_id') and provider_conn.backend_provider_id
                else str(provider_conn.id)
            )
            original_id = str(entity_dict.get("id", ""))
            if ":" not in original_id:
                entity_dict["id"] = f"{provider_id_prefix}:{original_id}"
            entity_dict["provider_id"] = str(provider_conn.id)
            entity_dict["provider_name"] = provider_conn.name
            return entity_dict
        
        if provider_id:
            # Provider ID specified - use that provider
            provider_conn = self.get_provider_by_id(provider_id)
            if provider_conn:
                try:
                    provider = self.create_provider_instance(provider_conn)
                    sprint = await provider.get_sprint(actual_id)
                    if sprint:
                        sprint_dict = self._to_dict(sprint)
                        return _wrap_composite_id(sprint_dict, provider_conn)
                except Exception as e:
                    self.record_error(provider_id, e)
        else:
            # No provider ID - iterate all active providers
            for provider_conn in self.get_active_providers():
                try:
                    provider = self.create_provider_instance(provider_conn)
                    sprint = await provider.get_sprint(actual_id)
                    if sprint:
                        sprint_dict = self._to_dict(sprint)
                        return _wrap_composite_id(sprint_dict, provider_conn)
                except Exception as e:
                    self.record_error(str(provider_conn.id), e)
                    continue
        
        return None
    
    # ==================== Users ====================
    
    async def list_users(
        self,
        project_id: Optional[str] = None,
        provider_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """List users from providers (streaming)."""
        import time
        from ..utils.data_buffer import DataBuffer, ensure_async_iterator
        
        run_id = f"run_{int(time.time())}"
        logger.info(f"[PM-DEBUG][{run_id}] list_users START: project_id={project_id}")
        
        buffer = DataBuffer(prefix="users_")
        
        provider_id_from_project = None
        actual_project_id = None
        if project_id:
            provider_id_from_project, actual_project_id = self._parse_composite_id(project_id)
        
        target_provider_id = provider_id or provider_id_from_project
        if target_provider_id:
            p_conn = self.get_provider_by_id(target_provider_id)
            providers = [p_conn] if p_conn else []
        else:
            providers = self.get_active_providers()

        for provider_conn in providers:
            try:
                provider = self.create_provider_instance(provider_conn)
                if not hasattr(provider, 'list_users'):
                    continue

                logger.info(f"[PM-DEBUG][{run_id}] Streaming users from {provider_conn.name}...")
                
                raw_result = provider.list_users(project_id=actual_project_id)
                
                async def enriched_iterator():
                    async for user in ensure_async_iterator(raw_result):
                        try:
                            u_dict = self._to_dict(user)
                            original_id = str(u_dict.get("id", ""))
                            if ":" not in original_id:
                                 provider_id_prefix = (
                                     str(provider_conn.backend_provider_id) 
                                     if hasattr(provider_conn, 'backend_provider_id') and provider_conn.backend_provider_id
                                     else str(provider_conn.id)
                                 )
                                 u_dict["id"] = f"{provider_id_prefix}:{original_id}"
                            u_dict["provider_id"] = str(provider_conn.id)
                            yield u_dict
                        except Exception as e:
                            logger.error(f"Error enriching user: {e}")
                
                await buffer.write_items(enriched_iterator())

            except PermissionError as e:
                 logger.error(f"[{provider_conn.name}] Permission Error: {e}")
                 # For streaming, we might record error but continue?
                 # Legacy raised it. If we raise, we break other providers.
                 # Let's record and continue to ensure partial data if possible,
                 # or re-raise if critical? 
                 # Given architecture goal is robustness, we record exception and move on?
                 # The original raised it. I will record it.
                 self.record_error(str(provider_conn.id), e)
                 
            except Exception as e:
                logger.error(f"Error listing users from {provider_conn.name}: {e}")
                self.record_error(str(provider_conn.id), e)
        
        users = await buffer.read_all()
        buffer.cleanup()
        logger.info(f"[PM-DEBUG][{run_id}] list_users END: Total users={len(users)}")
        return users
    
    async def get_user(self, user_id: str) -> Optional[dict[str, Any]]:
        """Get user by ID. Returns user with composite ID (provider:shortId) for multi-provider safety."""
        provider_id, actual_id = self._parse_composite_id(user_id)
        
        if provider_id:
            provider_conn = self.get_provider_by_id(provider_id)
            if provider_conn:
                try:
                    provider = self.create_provider_instance(provider_conn)
                    user = await provider.get_user(actual_id)
                    if user:
                        user_dict = self._to_dict(user)
                        # Ensure ID is composite for multi-provider safety
                        provider_id_prefix = (
                            str(provider_conn.backend_provider_id) 
                            if hasattr(provider_conn, 'backend_provider_id') and provider_conn.backend_provider_id
                            else str(provider_conn.id)
                        )
                        original_id = str(user_dict.get("id", ""))
                        if ":" not in original_id:
                            user_dict["id"] = f"{provider_id_prefix}:{original_id}"
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
        provider_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """List epics from providers (streaming)."""
        import time
        from ..utils.data_buffer import DataBuffer, ensure_async_iterator
        
        run_id = f"run_{int(time.time())}"
        logger.info(f"[PM-DEBUG][{run_id}] list_epics START: project_id={project_id}")
        
        buffer = DataBuffer(prefix="epics_")
        
        provider_id_from_project = None
        actual_project_id = None
        if project_id:
            provider_id_from_project, actual_project_id = self._parse_composite_id(project_id)
        
        target_provider_id = provider_id or provider_id_from_project
        if target_provider_id:
            p_conn = self.get_provider_by_id(target_provider_id)
            providers = [p_conn] if p_conn else []
        else:
            providers = self.get_active_providers()
            
        for provider_conn in providers:
            try:
                provider = self.create_provider_instance(provider_conn)
                if not hasattr(provider, 'list_epics'):
                    continue

                logger.info(f"[PM-DEBUG][{run_id}] Streaming epics from {provider_conn.name}...")
                
                raw_result = provider.list_epics(project_id=actual_project_id)
                
                async def enriched_iterator():
                    async for epic in ensure_async_iterator(raw_result):
                        try:
                            e_dict = self._to_dict(epic)
                            # Enrich ID
                            original_id = str(e_dict.get("id", ""))
                            if ":" not in original_id:
                                provider_id_prefix = (
                                    str(provider_conn.backend_provider_id) 
                                    if hasattr(provider_conn, 'backend_provider_id') and provider_conn.backend_provider_id
                                    else str(provider_conn.id)
                                )
                                e_dict["id"] = f"{provider_id_prefix}:{original_id}"
                                
                                # Normalize References
                                if e_dict.get("project_id") and ":" not in str(e_dict.get("project_id")):
                                    e_dict["project_id"] = f"{provider_id_prefix}:{e_dict.get('project_id')}"
                            
                            e_dict["provider_id"] = str(provider_conn.id)
                            e_dict["provider_name"] = provider_conn.name
                            yield e_dict
                        except Exception as e:
                            logger.error(f"Error enriching epic: {e}")
                
                await buffer.write_items(enriched_iterator())

            except Exception as e:
                logger.error(f"Error fetching epics from {provider_conn.name}: {e}")
                self.record_error(str(provider_conn.id), e)
                
        epics = await buffer.read_all()
        buffer.cleanup()
        logger.info(f"[PM-DEBUG][{run_id}] list_epics END: Total epics={len(epics)}")
        return epics
    
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

    # ==================== Time Entries ====================
    
    async def list_time_entries(
        self,
        provider_id: Optional[str] = None,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        List time entries from providers with buffered storage.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # If specific provider requested
        if provider_id:
            providers = [self.get_provider_by_id(provider_id)]
            providers = [p for p in providers if p]
        else:
            providers = self.get_active_providers()
            
        # Parse composite IDs if provided
        actual_task_id = None
        if task_id:
            pid, actual_task_id = self._parse_composite_id(task_id)
            if pid and not provider_id:
                # If specific provider implied by task ID, filter providers? 
                # Original logic didn't filter explicitly here but did parsing.
                # We'll stick to logic: filter only if provider_id explicitly passed or we want to optimize.
                pass
        
        actual_user_id = None
        if user_id:
             _, actual_user_id = self._parse_composite_id(user_id)
             
        actual_project_id = None
        if project_id:
             _, actual_project_id = self._parse_composite_id(project_id)

        from ..utils.data_buffer import DataBuffer
        buffer = DataBuffer(prefix="time_")
        
        for provider_conn in providers:
            try:
                # Create provider instance
                provider = self.create_provider_instance(provider_conn)
                
                if hasattr(provider, 'get_time_entries'):
                    logger.info(f"[PM-DEBUG] Streaming time entries from {provider_conn.name}...")
                    
                    # Async iterator call
                    iterator = provider.get_time_entries(
                        task_id=actual_task_id,
                        user_id=actual_user_id,
                        project_id=actual_project_id,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    # Wrapper generator to inject provider info
                    async def enriched_iterator():
                        async for entry in iterator:
                            # Convert pydantic if needed
                            if hasattr(entry, 'dict'):
                                d = entry.dict()
                            elif hasattr(entry, 'model_dump'):
                                d = entry.model_dump()
                            else:
                                d = dict(entry)
                            
                            # Get provider_id prefix for normalizing IDs
                            provider_id_prefix = (
                                str(provider_conn.backend_provider_id) 
                                if hasattr(provider_conn, 'backend_provider_id') and provider_conn.backend_provider_id
                                else str(provider_conn.id)
                            )
                            
                            # Normalize user_id with provider prefix
                            raw_user_id = d.get("user_id")
                            if raw_user_id and ":" not in str(raw_user_id):
                                d["user_id"] = f"{provider_id_prefix}:{raw_user_id}"
                            
                            # Normalize task_id with provider prefix
                            raw_task_id = d.get("task_id")
                            if raw_task_id and ":" not in str(raw_task_id):
                                d["task_id"] = f"{provider_id_prefix}:{raw_task_id}"
                            
                            d["provider_id"] = str(provider_conn.id)
                            d["provider_name"] = provider_conn.name
                            yield d
                            
                    count = await buffer.write_items(enriched_iterator())
                    logger.info(f"[PM-DEBUG] Streamed {count} entries from {provider_conn.name}")
                    
            except Exception as e:
                self.record_error(str(provider_conn.id), e)
                logger.error(f"Error streaming time entries from {provider_conn.name}: {e}")
                continue
        
        # Read all items from buffer to return list
        entries = await buffer.read_all()
        buffer.cleanup()
        return entries

    async def log_time_entry(
        self,
        task_id: str,
        hours: float,
        comment: Optional[str] = None,
        activity_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """Log time entry."""
        provider_id, actual_task_id = self._parse_composite_id(task_id)
        
        if not provider_id:
            raise ValueError("task_id must include provider_id")
            
        provider_conn = self.get_provider_by_id(provider_id)
        if not provider_conn:
            raise ValueError(f"Provider {provider_id} not found")
            
        provider = self.create_provider_instance(provider_conn)
        
        if not hasattr(provider, 'log_time_entry'):
            raise ValueError(f"Provider {provider_conn.provider_type} does not support logging time")
            
        actual_user_id = None
        if user_id:
            _, actual_user_id = self._parse_composite_id(user_id)
            
        entry = await provider.log_time_entry(
            task_id=actual_task_id,
            hours=hours,
            comment=comment,
            activity_id=activity_id,
            user_id=actual_user_id
        )
        
        if entry:
            entry_dict = self._to_dict(entry)
            entry_dict["provider_id"] = str(provider_conn.id)
            entry_dict["provider_name"] = provider_conn.name
            return entry_dict
            
        return None
