# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
PM Handler - Unified abstraction layer for PM providers

This module provides a unified interface for interacting with PM providers,
abstracting away the complexity of provider management from both:
- API endpoints (multi-provider aggregation)
- Conversation/Agent flows (single provider context)

PMHandler serves as the parent/adapter layer that sits above individual
pm_providers, providing a consistent interface regardless of whether you're
working with a single provider or aggregating across multiple providers.
"""

import logging
from datetime import date
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session

from database.orm_models import PMProviderConnection
from pm_providers.factory import create_pm_provider
from pm_providers.base import BasePMProvider
from pm_providers.builder import build_pm_provider
from pm_providers.models import PMTask, PMProject, PMSprint

logger = logging.getLogger(__name__)


class PMHandler:
    """
    Unified handler for PM providers - parent abstraction layer.
    
    This class provides a unified interface for interacting with PM providers,
    supporting both:
    - Single provider mode (for agents/conversation flows)
    - Multi-provider mode (for API endpoints aggregating data)
    
    It serves as the primary abstraction layer that sits above individual
    pm_provider implementations, providing a consistent interface regardless
    of the underlying provider(s).
    """
    
    def __init__(
        self, 
        db_session: Optional[Session] = None,
        single_provider: Optional[BasePMProvider] = None,
        user_id: Optional[str] = None
    ):
        """
        Initialize PM handler.
        
        Args:
            db_session: Database session for querying PM provider connections.
                       Required for multi-provider mode.
            single_provider: Optional single provider instance to use.
                            If provided, operates in single-provider mode.
                            If None, operates in multi-provider mode using db_session.
            user_id: Optional user ID to filter providers by user.
                     If provided, only returns providers where created_by = user_id.
                     If None, returns all active providers (backward compatible).
        """
        self.db = db_session
        self.single_provider = single_provider
        self.user_id = user_id
        self._mode = "single" if single_provider else "multi"
    
    
    @classmethod
    def from_single_provider(
        cls, 
        provider: BasePMProvider
    ) -> "PMHandler":
        """
        Create PMHandler instance for single provider mode.
        
        This is useful for agent/conversation flows that work with one provider.
        
        Args:
            provider: Single PM provider instance
            
        Returns:
            PMHandler configured for single-provider mode
        """
        return cls(single_provider=provider)
    
    @classmethod
    def from_db_session(
        cls,
        db_session: Session,
        user_id: Optional[str] = None
    ) -> "PMHandler":
        """
        Create PMHandler instance for multi-provider mode.
        
        This aggregates data from active providers in the database.
        If user_id is provided, only aggregates from that user's providers.
        
        Args:
            db_session: Database session for querying providers
            user_id: Optional user ID to filter providers by user.
                     If None, aggregates from all active providers.
            
        Returns:
            PMHandler configured for multi-provider mode
        """
        return cls(db_session=db_session, user_id=user_id)
    
    @classmethod
    def from_db_session_and_user(
        cls,
        db_session: Session,
        user_id: str
    ) -> "PMHandler":
        """
        Create PMHandler instance for specific user.
        
        This is a convenience method that explicitly creates a user-scoped handler.
        Only returns providers where created_by = user_id.
        
        Args:
            db_session: Database session for querying providers
            user_id: User ID to filter providers
            
        Returns:
            PMHandler configured for user-scoped multi-provider mode
        """
        return cls(db_session=db_session, user_id=user_id)
    
    def _get_active_providers(self) -> List[PMProviderConnection]:
        """
        Get active PM providers from database.
        
        If user_id is set, only returns providers where created_by = user_id.
        Otherwise, returns all active providers (backward compatible).
        """
        if not self.db:
            return []
        
        query = self.db.query(PMProviderConnection).filter(
            PMProviderConnection.is_active.is_(True)
        )
        
        # Filter by user if user_id is provided
        if self.user_id:
            query = query.filter(
                PMProviderConnection.created_by == self.user_id
            )
            logger.info(f"[PMHandler] Filtering providers by user_id: {self.user_id}")
        
        providers = query.all()
        logger.info(f"[PMHandler] Found {len(providers)} active provider(s)")
        return providers
    
    def _create_provider_instance(self, provider: PMProviderConnection):
        """
        Create a PM provider instance from database provider connection.
        
        Args:
            provider: PMProviderConnection from database
            
        Returns:
            Configured PM provider instance
        """
        # Prepare API key - handle empty strings and None
        api_key_value = None
        if provider.api_key:
            api_key_str = str(provider.api_key).strip()
            api_key_value = api_key_str if api_key_str else None
        
        api_token_value = None
        if provider.api_token:
            api_token_str = str(provider.api_token).strip()
            api_token_value = api_token_str if api_token_str else None
        
        # Handle username - check for None and empty strings
        username_value = None
        if provider.username:
            username_str = str(provider.username).strip()
            username_value = username_str if username_str else None
        
        logger.info(
            f"[PMHandler._create_provider_instance] Creating provider: "
            f"type={provider.provider_type}, "
            f"username={username_value}, "
            f"has_api_token={bool(api_token_value)}"
        )
        
        return create_pm_provider(
            provider_type=str(provider.provider_type),
            base_url=str(provider.base_url),
            api_key=api_key_value,
            api_token=api_token_value,
            username=username_value,
            organization_id=(
                str(provider.organization_id)
                if provider.organization_id
                else None
            ),
            workspace_id=(
                str(provider.workspace_id)
                if provider.workspace_id
                else None
            ),
        )
    
    def _get_provider_for_project(self, project_id: str):
        """
        Get provider instance for a project_id.
        
        Args:
            project_id: Project ID in format "provider_id:actual_project_id"
            
        Returns:
            PM provider instance
            
        Raises:
            ValueError: If provider_id format is invalid or provider not found
        """
        if ":" not in project_id:
            raise ValueError(f"Invalid project_id format: {project_id}")
        
        parts = project_id.split(":", 1)
        provider_id_str = parts[0]
        
        from uuid import UUID
        try:
            provider_uuid = UUID(provider_id_str)
        except ValueError:
            raise ValueError(f"Invalid provider ID format: {provider_id_str}")
        
        provider = self.db.query(PMProviderConnection).filter(
            PMProviderConnection.id == provider_uuid,
            PMProviderConnection.is_active.is_(True)
        ).first()
        
        if not provider:
            raise ValueError(f"Provider not found: {provider_id_str}")
        
        # Log what we're getting from the database for debugging
        logger.info(
            f"[PMHandler._get_provider_for_project] Provider found: "
            f"type={provider.provider_type}, "
            f"username={repr(provider.username)}, "
            f"has_username={bool(provider.username)}, "
            f"username_stripped={repr(str(provider.username).strip() if provider.username else None)}"
        )
        
        return self._create_provider_instance(provider)
    
    async def list_all_projects(self) -> List[Dict[str, Any]]:
        """
        List all projects.
        
        In single-provider mode: Returns projects from the single provider.
        In multi-provider mode: Returns projects from all active providers.
        
        Returns:
            List of projects with provider_id prefix in project.id (multi-mode)
            or plain project IDs (single-mode)
        """
        if self._mode == "single":
            # Single provider mode
            if not self.single_provider:
                return []
            
            projects = await self.single_provider.list_projects()
            # Get provider type from config if available
            provider_type = "unknown"
            if hasattr(self.single_provider, 'config') and self.single_provider.config:
                provider_type = getattr(self.single_provider.config, 'provider_type', 'unknown')
            elif hasattr(self.single_provider, '__class__'):
                # Fallback: use class name
                class_name = self.single_provider.__class__.__name__
                provider_type = class_name.replace('Provider', '').lower() if 'Provider' in class_name else class_name.lower()
            
            return [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "description": p.description or "",
                    "status": (
                        p.status.value
                        if p.status and hasattr(p.status, 'value')
                        else str(p.status) if p.status else "None"
                    ),
                    "provider_id": "single",
                    "provider_type": provider_type,
                }
                for p in projects
            ]
        
        # Multi-provider mode
        providers = self._get_active_providers()
        
        if not providers:
            return []
        
        all_projects = []

        for provider in providers:
            try:
                provider_instance = self._create_provider_instance(provider)
                projects = await provider_instance.list_projects()
                
                # Prefix project ID with provider_id to ensure uniqueness
                for p in projects:
                    all_projects.append({
                        "id": f"{provider.id}:{p.id}",
                        "name": p.name,
                        "description": p.description or "",
                        "status": (
                            p.status.value
                            if p.status and hasattr(p.status, 'value')
                            else str(p.status) if p.status else "None"
                        ),
                        "provider_id": str(provider.id),
                        "provider_type": provider.provider_type,
                    })
            except Exception as provider_error:
                logger.warning(
                    f"Failed to fetch projects from provider "
                    f"{provider.id} ({provider.provider_type}): "
                    f"{provider_error}"
                )
                continue
        
        return all_projects
    
    async def list_all_tasks(self) -> List[Dict[str, Any]]:
        """
        List all tasks from all active PM providers.
        
        Returns:
            List of tasks with project_name mapped from all providers
        """
        providers = self._get_active_providers()
        
        if not providers:
            return []
        
        all_tasks = []
        all_projects_map = {}  # Map project_id to project_name across all providers
        
        for provider in providers:
            try:
                provider_instance = self._create_provider_instance(provider)
                
                # Fetch projects for this provider to build name mapping
                projects = await provider_instance.list_projects()
                for p in projects:
                    # Store with provider_id prefix to ensure uniqueness
                    prefixed_id = f"{provider.id}:{p.id}"
                    all_projects_map[prefixed_id] = p.name
                    # Also store without prefix for backward compatibility
                    all_projects_map[p.id] = p.name
                
                # Fetch all tasks from this provider (no project filter)
                all_provider_tasks = []
                try:
                    # Try fetching all tasks without project filter (works for OpenProject)
                    tasks = await provider_instance.list_tasks()
                    all_provider_tasks = tasks
                except Exception as e:
                    error_msg = str(e).lower()
                    # If JIRA requires project-specific queries, fetch per project
                    if "unbounded" in error_msg or "search restriction" in error_msg:
                        logger.info(
                            f"Provider {provider.provider_type} requires project-specific queries. "
                            f"Fetching tasks per project..."
                        )
                        # Fetch tasks for each project
                        for project in projects:
                            try:
                                project_tasks = await provider_instance.list_tasks(
                                    project_id=project.id
                                )
                                all_provider_tasks.extend(project_tasks)
                            except Exception as project_error:
                                logger.warning(
                                    f"Failed to fetch tasks for project {project.id} "
                                    f"from provider {provider.id}: {project_error}"
                                )
                                continue
                    else:
                        # Re-raise if it's a different error
                        raise
                
                tasks = all_provider_tasks
                
                # Add tasks with project_name mapping
                for task in tasks:
                    task_project_id = task.project_id
                    project_name = "Unknown"
                    prefixed_project_id = None
                    
                    if task_project_id:
                        # Try with provider prefix first
                        prefixed_id = f"{provider.id}:{task_project_id}"
                        if prefixed_id in all_projects_map:
                            project_name = all_projects_map[prefixed_id]
                            prefixed_project_id = prefixed_id
                        elif task_project_id in all_projects_map:
                            project_name = all_projects_map[task_project_id]
                            prefixed_project_id = prefixed_id  # Use prefixed format for consistency
                        else:
                            # Use prefixed format even if not in map
                            prefixed_project_id = prefixed_id
                    
                    task_dict = self._task_to_dict(
                        task, 
                        project_name,
                        project_id=prefixed_project_id or (str(task_project_id) if task_project_id else None)
                    )
                    # Extract assignee name from raw_data if available
                    if task.assignee_id:
                        assignee_name = self._extract_assignee_name_from_raw_data(task)
                        if assignee_name:
                            task_dict["assigned_to"] = assignee_name
                    all_tasks.append(task_dict)
                        
            except Exception as provider_error:
                logger.warning(
                    f"Failed to fetch tasks from provider "
                    f"{provider.id} ({provider.provider_type}): {provider_error}"
                )
                continue
        
        return all_tasks
    
    async def list_my_tasks(self) -> List[Dict[str, Any]]:
        """
        List all tasks assigned to the current user across all active providers.
        
        This method:
        1. Lists all active PM providers
        2. For each provider, gets the current user (via get_current_user())
        3. Fetches all tasks assigned to that user (via list_tasks(assignee_id=current_user.id))
        4. Converts tasks to dictionaries with project_id included
        5. Returns aggregated list of all tasks
        
        Returns:
            List of task dictionaries, each with project_id field included
        """
        logger.info("=" * 80)
        logger.info("[PMHandler] list_my_tasks() called")
        logger.info(f"[PMHandler] Mode: {self._mode}")
        logger.info("=" * 80)
        if self._mode == "single":
            # Single provider mode
            if not self.single_provider:
                return []
            
            current_user = await self.single_provider.get_current_user()
            if not current_user:
                logger.warning("Cannot determine current user - get_current_user() returned None")
                return []
            
            logger.info(
                f"Getting tasks for current user: ID={current_user.id}, Name={current_user.name}, "
                f"Provider={self.single_provider.__class__.__name__}"
            )
            logger.debug(
                f"[list_my_tasks] Single provider mode: "
                f"Provider class: {self.single_provider.__class__.__name__}, "
                f"User ID: {current_user.id}, User Name: {current_user.name}"
            )
            
            projects = await self.single_provider.list_projects()
            project_map = {p.id: p.name for p in projects}
            logger.debug(f"[list_my_tasks] Listed {len(projects)} projects for name mapping")
            
            try:
                logger.debug(
                    f"[list_my_tasks] Calling provider.list_tasks(assignee_id={current_user.id}) "
                    f"to get tasks assigned to current user"
                )
                tasks = await self.single_provider.list_tasks(
                    assignee_id=current_user.id
                )
                logger.info(
                    f"Retrieved {len(tasks)} tasks from API with assignee filter (user_id={current_user.id})"
                )
                logger.debug(
                    f"[list_my_tasks] Provider returned {len(tasks)} tasks. "
                    f"Sample task IDs: {[str(t.id) for t in tasks[:3]]}"
                )
            except Exception as e:
                error_msg = str(e).lower()
                if "unbounded" in error_msg or "search restriction" in error_msg:
                    # Fetch per project
                    tasks = []
                    for project in projects:
                        try:
                            project_tasks = await self.single_provider.list_tasks(
                                project_id=project.id,
                                assignee_id=current_user.id
                            )
                            tasks.extend(project_tasks)
                        except Exception:
                            continue
                else:
                    raise
            
            # CRITICAL: Post-filter to ensure only tasks actually assigned to current user are returned
            # This is a safeguard in case the API filter doesn't work correctly or returns tasks with null assignees
            # For JIRA: handle multiple ID formats (accountId, key, id) - check all possible formats
            current_user_id_str = str(current_user.id)
            
            # For JIRA, get current user accountId from raw_data if available (for better matching)
            provider_type = getattr(self.single_provider, 'config', None)
            provider_type = getattr(provider_type, 'provider_type', None) if provider_type else None
            current_user_account_id = None
            if provider_type == "jira" and hasattr(current_user, 'raw_data'):
                raw_data = getattr(current_user, 'raw_data', {})
                if isinstance(raw_data, dict):
                    current_user_account_id = raw_data.get("accountId")
            
            def is_task_assigned_to_user(task_assignee_id: Optional[str]) -> bool:
                """Check if task assignee ID matches current user (handles multiple ID formats)"""
                if not task_assignee_id:
                    return False
                
                task_assignee_str = str(task_assignee_id)
                
                # Exact match
                if task_assignee_str == current_user_id_str:
                    return True
                
                # For JIRA: also check accountId format
                if provider_type == "jira" and current_user_account_id:
                    if task_assignee_str == str(current_user_account_id):
                        return True
                
                return False
            
            filtered_tasks = [
                task for task in tasks
                if is_task_assigned_to_user(task.assignee_id)
            ]
            
            if len(filtered_tasks) != len(tasks):
                # Log detailed information about filtered tasks for debugging
                logger.warning(
                    f"Filtered out {len(tasks) - len(filtered_tasks)} tasks that were not "
                    f"assigned to current user (ID: {current_user_id_str}, Name: {current_user.name}"
                    f"{', accountId: ' + str(current_user_account_id) if current_user_account_id else ''}). "
                    f"Original count: {len(tasks)}, Filtered count: {len(filtered_tasks)}"
                )
                # Log sample of tasks that were filtered out
                filtered_out = [t for t in tasks if not is_task_assigned_to_user(t.assignee_id)]
                for task in filtered_out[:5]:  # Log first 5 for debugging
                    logger.debug(
                        f"  Filtered out task: ID={task.id}, Title={task.title}, "
                        f"AssigneeID={task.assignee_id} (expected: {current_user_id_str}"
                        f"{' or ' + str(current_user_account_id) if current_user_account_id else ''})"
                    )
            
            # Build assignee map with fallback to raw_data
            assignee_map = {}
            for task in filtered_tasks:
                if task.assignee_id and task.assignee_id not in assignee_map:
                    try:
                        user = await self.single_provider.get_user(task.assignee_id)
                        if user:
                            assignee_map[task.assignee_id] = user.name
                    except (NotImplementedError, Exception):
                        # Fallback: extract from raw_data
                        assignee_name = self._extract_assignee_name_from_raw_data(task)
                        if assignee_name:
                            assignee_map[task.assignee_id] = assignee_name
            
            # Get provider ID for composite project_id format
            provider_id = None
            if hasattr(self.single_provider, 'config') and hasattr(self.single_provider.config, 'provider_id'):
                provider_id = str(self.single_provider.config.provider_id)
            
            result = [
                {**self._task_to_dict(
                    task, 
                    project_map.get(task.project_id, "Unknown"),
                    project_id=f"{provider_id}:{task.project_id}" if (provider_id and task.project_id) else (str(task.project_id) if task.project_id else None)
                ), 
                "assigned_to": assignee_map.get(task.assignee_id) if task.assignee_id else None}
                for task in filtered_tasks
            ]
            
            logger.info("=" * 80)
            logger.info(f"[PMHandler] Single-provider mode: Returning {len(result)} tasks")
            if result:
                logger.info(f"[PMHandler] Sample task project_ids: {[t.get('project_id') for t in result[:3]]}")
            logger.info("=" * 80)
            
            return result
        
        # Multi-provider mode
        providers = self._get_active_providers()
        logger.info("=" * 80)
        logger.info(f"[PMHandler] Multi-provider mode: Found {len(providers)} active providers")
        logger.info("=" * 80)
        logger.debug(f"[list_my_tasks] Multi-provider mode: Found {len(providers)} active providers")
        
        if not providers:
            logger.warning("[list_my_tasks] No active providers found in multi-provider mode")
            return []
        
        all_tasks = []
        all_projects_map = {}  # Map project_id to project_name across all providers
        
        logger.debug(
            f"[list_my_tasks] Starting multi-provider task retrieval. "
            f"Will process {len(providers)} providers: "
            f"{[(p.id, p.provider_type) for p in providers]}"
        )
        
        for provider in providers:
            logger.debug(
                f"[list_my_tasks] Processing provider: {provider.id} ({provider.provider_type})"
            )
            try:
                logger.debug(f"[list_my_tasks] Creating provider instance for {provider.id}")
                provider_instance = self._create_provider_instance(provider)
                
                # Get current user for this provider
                try:
                    logger.info(
                        f"Attempting to get current user for provider "
                        f"{provider.id} ({provider.provider_type})..."
                    )
                    logger.debug(
                        f"[list_my_tasks] Calling provider.get_current_user() for "
                        f"provider {provider.id} ({provider.provider_type})"
                    )
                    current_user = await provider_instance.get_current_user()
                    if not current_user:
                        logger.warning(
                            f"Cannot determine current user for provider "
                            f"{provider.id} ({provider.provider_type}). "
                            f"get_current_user() returned None. "
                            f"Skipping my tasks for this provider."
                        )
                        logger.debug(
                            f"[list_my_tasks] Provider {provider.id} returned None for get_current_user(). "
                            f"Skipping this provider."
                        )
                        continue
                    else:
                        logger.info(
                            f"Successfully retrieved current user for provider "
                            f"{provider.id} ({provider.provider_type}): "
                            f"id={current_user.id}, name={current_user.name}"
                        )
                        logger.debug(
                            f"[list_my_tasks] Current user for provider {provider.id}: "
                            f"ID={current_user.id}, Name={current_user.name}"
                        )
                except Exception as user_error:
                    logger.warning(
                        f"Failed to get current user for provider "
                        f"{provider.id} ({provider.provider_type}): {user_error}",
                        exc_info=True
                    )
                    continue
                
                # Fetch projects for this provider to build name mapping
                logger.debug(
                    f"[list_my_tasks] Fetching projects for provider {provider.id} to build name mapping"
                )
                projects = await provider_instance.list_projects()
                logger.debug(
                    f"[list_my_tasks] Provider {provider.id} has {len(projects)} projects"
                )
                for p in projects:
                    # Store with provider_id prefix to ensure uniqueness
                    prefixed_id = f"{provider.id}:{p.id}"
                    all_projects_map[prefixed_id] = p.name
                    # Also store without prefix for backward compatibility
                    all_projects_map[p.id] = p.name
                logger.debug(
                    f"[list_my_tasks] Built project map with {len(all_projects_map)} entries "
                    f"for provider {provider.id}"
                )
                
                # Fetch tasks assigned to current user
                all_provider_tasks = []
                try:
                    logger.debug(
                        f"[list_my_tasks] Calling provider.list_tasks(assignee_id={current_user.id}) "
                        f"for provider {provider.id} to get tasks assigned to current user"
                    )
                    tasks = await provider_instance.list_tasks(
                        assignee_id=current_user.id
                    )
                    all_provider_tasks = tasks
                    logger.debug(
                        f"[list_my_tasks] Provider {provider.id} returned {len(tasks)} tasks "
                        f"with assignee_id={current_user.id}"
                    )
                except Exception as e:
                    error_msg = str(e).lower()
                    logger.debug(
                        f"[list_my_tasks] Provider {provider.id} list_tasks(assignee_id) failed: {error_msg}. "
                        f"Will try per-project approach if needed."
                    )
                    # If JIRA requires project-specific queries, fetch per project
                    if "unbounded" in error_msg or "search restriction" in error_msg:
                        logger.info(
                            f"Provider {provider.provider_type} requires project-specific queries. "
                            f"Fetching my tasks per project..."
                        )
                        logger.debug(
                            f"[list_my_tasks] Fetching tasks per project for provider {provider.id}. "
                            f"Total projects: {len(projects)}"
                        )
                        # Fetch tasks for each project with assignee filter
                        for project in projects:
                            try:
                                logger.debug(
                                    f"[list_my_tasks] Fetching tasks for project {project.id} "
                                    f"with assignee_id={current_user.id}"
                                )
                                project_tasks = await provider_instance.list_tasks(
                                    project_id=project.id,
                                    assignee_id=current_user.id
                                )
                                all_provider_tasks.extend(project_tasks)
                                logger.debug(
                                    f"[list_my_tasks] Project {project.id} returned {len(project_tasks)} tasks"
                                )
                            except Exception as project_error:
                                logger.warning(
                                    f"Failed to fetch my tasks for project {project.id} "
                                    f"from provider {provider.id}: {project_error}"
                                )
                                continue
                    else:
                        # Re-raise if it's a different error
                        raise
                
                tasks = all_provider_tasks
                
                # CRITICAL: Post-filter to ensure only tasks actually assigned to current user are returned
                # This is a safeguard in case the API filter doesn't work correctly or returns tasks with null assignees
                # For JIRA: handle multiple ID formats (accountId, key, id) - check all possible formats
                current_user_id_str = str(current_user.id)
                
                # For JIRA, get current user accountId from raw_data if available (for better matching)
                current_user_account_id = None
                if provider.provider_type == "jira" and hasattr(current_user, 'raw_data'):
                    raw_data = getattr(current_user, 'raw_data', {})
                    if isinstance(raw_data, dict):
                        current_user_account_id = raw_data.get("accountId")
                
                def is_task_assigned_to_user(task_assignee_id: Optional[str]) -> bool:
                    """Check if task assignee ID matches current user (handles multiple ID formats)"""
                    if not task_assignee_id:
                        return False
                    
                    task_assignee_str = str(task_assignee_id)
                    
                    # Exact match
                    if task_assignee_str == current_user_id_str:
                        return True
                    
                    # For JIRA: also check accountId format
                    if provider.provider_type == "jira" and current_user_account_id:
                        if task_assignee_str == str(current_user_account_id):
                            return True
                    
                    return False
                
                filtered_tasks = [
                    task for task in tasks
                    if is_task_assigned_to_user(task.assignee_id)
                ]
                
                if len(filtered_tasks) != len(tasks):
                    # Log detailed information about filtered tasks for debugging
                    logger.warning(
                        f"Provider {provider.provider_type}: Filtered out {len(tasks) - len(filtered_tasks)} tasks "
                        f"that were not assigned to current user (ID: {current_user_id_str}, Name: {current_user.name}"
                        f"{', accountId: ' + str(current_user_account_id) if current_user_account_id else ''}). "
                        f"Original count: {len(tasks)}, Filtered count: {len(filtered_tasks)}"
                    )
                    # Log sample of tasks that were filtered out
                    filtered_out = [t for t in tasks if not is_task_assigned_to_user(t.assignee_id)]
                    for task in filtered_out[:5]:  # Log first 5 for debugging
                        logger.debug(
                            f"  Filtered out task: ID={task.id}, Title={task.title}, "
                            f"AssigneeID={task.assignee_id} (expected: {current_user_id_str}"
                            f"{' or ' + str(current_user_account_id) if current_user_account_id else ''})"
                        )
                
                logger.debug(
                    f"[list_my_tasks] Provider {provider.id}: "
                    f"Retrieved {len(tasks)} tasks, filtered to {len(filtered_tasks)} tasks assigned to user"
                )
                
                # Add tasks with project_name mapping
                for task in filtered_tasks:
                    task_project_id = task.project_id
                    project_name = "Unknown"
                    prefixed_project_id = None
                    
                    if task_project_id:
                        # Try with provider prefix first
                        prefixed_id = f"{provider.id}:{task_project_id}"
                        if prefixed_id in all_projects_map:
                            project_name = all_projects_map[prefixed_id]
                            prefixed_project_id = prefixed_id
                        elif task_project_id in all_projects_map:
                            project_name = all_projects_map[task_project_id]
                            prefixed_project_id = prefixed_id  # Use prefixed format for consistency
                        else:
                            # Use prefixed format even if not in map
                            prefixed_project_id = prefixed_id
                    
                    task_dict = self._task_to_dict(
                        task, 
                        project_name,
                        project_id=prefixed_project_id or (str(task_project_id) if task_project_id else None)
                    )
                    # Extract assignee name from raw_data if available
                    if task.assignee_id:
                        assignee_name = self._extract_assignee_name_from_raw_data(task)
                        if assignee_name:
                            task_dict["assigned_to"] = assignee_name
                    all_tasks.append(task_dict)
                
                logger.debug(
                    f"[list_my_tasks] Added {len(filtered_tasks)} tasks from provider {provider.id}. "
                    f"Total tasks so far: {len(all_tasks)}"
                )
                        
            except Exception as provider_error:
                logger.warning(
                    f"Failed to fetch my tasks from provider "
                    f"{provider.id} ({provider.provider_type}): {provider_error}"
                )
                logger.debug(
                    f"[list_my_tasks] Error details for provider {provider.id}: {provider_error}",
                    exc_info=True
                )
                continue
        
        logger.info("=" * 80)
        logger.info(f"[PMHandler] Multi-provider mode: Returning {len(all_tasks)} total tasks from {len(providers)} providers")
        if all_tasks:
            logger.info(f"[PMHandler] Sample task project_ids: {[t.get('project_id') for t in all_tasks[:5]]}")
        logger.info("=" * 80)
        logger.debug(
            f"[list_my_tasks] Final result: {len(all_tasks)} tasks from {len(providers)} providers. "
            f"Task project_ids: {[t.get('project_id') for t in all_tasks[:5]]}"
        )
        return all_tasks
    
    async def list_project_tasks(
        self, 
        project_id: str,
        assignee_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List tasks for a specific project.
        
        Args:
            project_id: Project ID in format "provider_id:actual_project_id"
            assignee_id: Optional assignee filter
            
        Returns:
            List of tasks for the project with assignee names mapped
        """
        # Parse project_id format: provider_id:actual_project_id
        provider_instance = self._get_provider_for_project(project_id)
        actual_project_id = (
            project_id.split(":", 1)[1]
            if ":" in project_id
            else project_id
        )
        
        # Fetch projects for name mapping
        projects = await provider_instance.list_projects()
        project_map = {p.id: p.name for p in projects}
        
        # Fetch tasks
        provider_type = getattr(getattr(provider_instance, "config", None), "provider_type", provider_instance.__class__.__name__)

        try:
            logger.info(
                "=" * 80
            )
            logger.info(
                "CALLING PROVIDER list_tasks: "
                "provider=%s, project_id=%s, actual_project_id=%s",
                provider_type, project_id, actual_project_id
            )
            logger.info("=" * 80)
            
            tasks = await provider_instance.list_tasks(
                project_id=actual_project_id,
                assignee_id=assignee_id
            )
            
            logger.info(
                "Provider returned %d tasks successfully",
                len(tasks) if tasks else 0
            )
            logger.info("=" * 80)
        except NotImplementedError:
            logger.warning(
                f"list_tasks not implemented for provider "
                f"{provider_type}"
            )
            raise ValueError(
                f"list_tasks is not yet implemented for "
                f"{provider_type} provider"
            )
        except Exception as list_error:
            error_msg = str(list_error)
            logger.error(
                f"Failed to list tasks for project {actual_project_id} "
                f"from provider {project_id.split(':')[0]} "
                f"(type: {provider_type}): {error_msg}"
            )
            import traceback
            logger.error(traceback.format_exc())
            
            # Extract HTTP status code from error message if present
            import re
            status_code = None
            status_patterns = [
                r'\((\d{3})\s+(?:Gone|Not Found|Unauthorized|Forbidden|'
                r'Bad Request|Client Error)\)',
                r'\((\d{3})\)',  # Check for status code like "(410)"
                r'\b(\d{3})\s+(?:Gone|Not Found|Unauthorized|Forbidden|'
                r'Bad Request|Client Error)',
                r'\b(?:status code|HTTP|status)\s*:?\s*(\d{3})\b',
            ]
            for pattern in status_patterns:
                match = re.search(pattern, error_msg, re.IGNORECASE)
                if match:
                    try:
                        status_code = int(match.group(1))
                        break
                    except (ValueError, IndexError):
                        continue
            
            # Re-raise with status code information in error message
            # The API layer will extract this and convert to HTTPException
            if status_code and 400 <= status_code < 600:
                raise ValueError(f"({status_code}) {error_msg}")
            else:
                raise ValueError(error_msg)
        
        # Build assignee map
        assignee_map = {}
        for task in tasks:
            if task.assignee_id and task.assignee_id not in assignee_map:
                try:
                    user = await provider_instance.get_user(task.assignee_id)
                    if user:
                        assignee_map[task.assignee_id] = user.name
                except (NotImplementedError, Exception):
                    # Fallback: Try to extract assignee name from task raw_data
                    # This is useful for providers like JIRA where get_user might not be implemented
                    assignee_name = self._extract_assignee_name_from_raw_data(task)
                    if assignee_name:
                        assignee_map[task.assignee_id] = assignee_name
                        logger.debug(
                            f"Extracted assignee name from raw_data: {assignee_name} "
                            f"for assignee_id {task.assignee_id}"
                        )
        
        # Map project names
        project_name = project_map.get(actual_project_id, "Unknown")
        
        # Convert tasks to dict with assignee names
        result = []
        for task in tasks:
            # Use the full project_id (with provider prefix) for consistency
            task_dict = self._task_to_dict(task, project_name, project_id=project_id)
            # Try assignee_map first, then fallback to raw_data extraction
            assigned_to = None
            if task.assignee_id:
                assigned_to = assignee_map.get(task.assignee_id)
                # If still not found, try extracting from this task's raw_data directly
                if not assigned_to:
                    assigned_to = self._extract_assignee_name_from_raw_data(task)
                    if assigned_to:
                        # Cache it for future use
                        assignee_map[task.assignee_id] = assigned_to
            
            task_dict["assigned_to"] = assigned_to
            result.append(task_dict)
        
        return result

    async def create_project_task(
        self,
        project_id: str,
        task_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new task within the specified project.
        """
        provider_instance = self._get_provider_for_project(project_id)
        provider_type = getattr(
            getattr(provider_instance, "config", None),
            "provider_type",
            provider_instance.__class__.__name__,
        )

        actual_project_id = (
            project_id.split(":", 1)[1]
            if ":" in project_id
            else project_id
        )

        title = task_data.get("title") or "New Task"
        new_task = PMTask(
            title=title,
            description=task_data.get("description"),
            priority=task_data.get("priority"),
            status=task_data.get("status"),
            project_id=actual_project_id,
            sprint_id=task_data.get("sprint_id"),
            assignee_id=task_data.get("assignee_id"),
            epic_id=task_data.get("epic_id"),
            estimated_hours=task_data.get("estimated_hours"),
        )

        try:
            created = await provider_instance.create_task(new_task)
        except NotImplementedError:
            raise ValueError(
                f"create_task is not yet implemented for {provider_type} provider"
            )
        except Exception as create_error:
            logger.error(
                "Failed to create task in project %s via provider %s: %s",
                actual_project_id,
                provider_type,
                create_error,
            )
            raise

        def _enum_to_str(value: Optional[Any]) -> Optional[str]:
            if value is None:
                return None
            if hasattr(value, "value"):
                return str(value.value)
            return str(value)

        return {
            "id": str(created.id) if created.id else None,
            "title": created.title,
            "description": created.description,
            "status": _enum_to_str(created.status),
            "priority": _enum_to_str(created.priority),
            "project_id": project_id,
            "sprint_id": str(created.sprint_id) if created.sprint_id else None,
            "assignee_id": str(created.assignee_id) if created.assignee_id else None,
            "epic_id": str(created.epic_id) if created.epic_id else None,
            "estimated_hours": created.estimated_hours,
            "created_at": (
                created.created_at.isoformat() if created.created_at else None
            ),
            "updated_at": (
                created.updated_at.isoformat() if created.updated_at else None
            ),
        }
    
    async def list_project_sprints(
        self, project_id: str, state: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List sprints for a specific project, optionally filtered by state.
        
        Args:
            project_id: Project ID in format "provider_id:actual_project_id"
            state: Optional state filter ("active", "closed", "future", or None for all)
            
        Returns:
            List of sprints for the project
        """
        # Parse project_id format: provider_id:actual_project_id
        provider_instance = self._get_provider_for_project(project_id)
        actual_project_id = (
            project_id.split(":", 1)[1]
            if ":" in project_id
            else project_id
        )
        
        # Fetch sprints with optional state filter
        sprints = await provider_instance.list_sprints(
            project_id=actual_project_id,
            state=state
        )
        
        return [
            {
                "id": str(s.id),
                "name": s.name,
                "start_date": s.start_date.isoformat() if s.start_date else None,
                "end_date": s.end_date.isoformat() if s.end_date else None,
                "status": (
                    s.status.value
                    if s.status and hasattr(s.status, 'value')
                    else str(s.status) if s.status else None
                ),
                "capacity_hours": s.capacity_hours,
                "planned_hours": s.planned_hours,
                "goal": s.goal,
            }
            for s in sprints
        ]
    
    async def list_project_epics(self, project_id: str) -> List[Dict[str, Any]]:
        """
        List epics for a specific project.
        
        Args:
            project_id: Project ID in format "provider_id:actual_project_id"
            
        Returns:
            List of epics for the project
        """
        provider_instance = self._get_provider_for_project(project_id)
        actual_project_id = (
            project_id.split(":", 1)[1]
            if ":" in project_id
            else project_id
        )

        try:
            epics = await provider_instance.list_epics(project_id=actual_project_id)
        except NotImplementedError:
            provider_type = getattr(
                getattr(provider_instance, "config", None),
                "provider_type",
                provider_instance.__class__.__name__
            )
            raise ValueError(f"Epics not yet implemented for {provider_type}")
        except Exception as e:
            raise ValueError(str(e))

        return [
            {
                "id": str(e.id),
                "name": e.name,
                "description": e.description,
                "status": (
                    e.status.value
                    if e.status and hasattr(e.status, 'value')
                    else str(e.status) if e.status else None
                ),
                "priority": (
                    e.priority.value
                    if e.priority and hasattr(e.priority, 'value')
                    else str(e.priority) if e.priority else None
                ),
                "start_date": e.start_date.isoformat() if e.start_date else None,
                "end_date": e.end_date.isoformat() if e.end_date else None,
            }
            for e in epics
        ]
    
    async def create_project_epic(
        self, project_id: str, epic_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new epic for a specific project.
        
        Args:
            project_id: Project ID in format "provider_id:actual_project_id"
            epic_data: Epic data (name, description, etc.)
            
        Returns:
            Created epic data
        """
        if ":" not in project_id:
            raise ValueError(f"Invalid project_id format: {project_id}")
        
        parts = project_id.split(":", 1)
        provider_id_str = parts[0]
        actual_project_id = parts[1]
        
        from uuid import UUID
        try:
            provider_uuid = UUID(provider_id_str)
        except ValueError:
            raise ValueError(f"Invalid provider ID format: {provider_id_str}")
        
        provider = self.db.query(PMProviderConnection).filter(
            PMProviderConnection.id == provider_uuid,
            PMProviderConnection.is_active.is_(True)
        ).first()
        
        if not provider:
            raise ValueError(f"Provider not found: {provider_id_str}")
        
        provider_instance = self._create_provider_instance(provider)
        
        # Convert epic_data to PMEpic
        from datetime import datetime
        from pm_providers.models import PMEpic
        
        epic = PMEpic(
            name=epic_data.get("name", ""),
            description=epic_data.get("description"),
            project_id=actual_project_id,
            start_date=(
                datetime.fromisoformat(epic_data["start_date"]).date()
                if epic_data.get("start_date")
                else None
            ),
            end_date=(
                datetime.fromisoformat(epic_data["end_date"]).date()
                if epic_data.get("end_date")
                else None
            ),
        )
        
        try:
            created_epic = await provider_instance.create_epic(epic)
        except NotImplementedError:
            raise ValueError(f"Epic creation not yet implemented for {provider.provider_type}")
        except Exception as e:
            raise ValueError(str(e))
        
        return {
            "id": str(created_epic.id),
            "name": created_epic.name,
            "description": created_epic.description,
            "status": (
                created_epic.status.value
                if created_epic.status and hasattr(created_epic.status, 'value')
                else str(created_epic.status) if created_epic.status else None
            ),
            "priority": (
                created_epic.priority.value
                if created_epic.priority and hasattr(created_epic.priority, 'value')
                else str(created_epic.priority) if created_epic.priority else None
            ),
            "start_date": created_epic.start_date.isoformat() if created_epic.start_date else None,
            "end_date": created_epic.end_date.isoformat() if created_epic.end_date else None,
        }
    
    async def update_project_epic(
        self, project_id: str, epic_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an epic for a specific project.
        
        Args:
            project_id: Project ID in format "provider_id:actual_project_id"
            epic_id: Epic ID
            updates: Updates to apply
            
        Returns:
            Updated epic data
        """
        if ":" not in project_id:
            raise ValueError(f"Invalid project_id format: {project_id}")
        
        parts = project_id.split(":", 1)
        provider_id_str = parts[0]
        
        from uuid import UUID
        try:
            provider_uuid = UUID(provider_id_str)
        except ValueError:
            raise ValueError(f"Invalid provider ID format: {provider_id_str}")
        
        provider = self.db.query(PMProviderConnection).filter(
            PMProviderConnection.id == provider_uuid,
            PMProviderConnection.is_active.is_(True)
        ).first()
        
        if not provider:
            raise ValueError(f"Provider not found: {provider_id_str}")
        
        provider_instance = self._create_provider_instance(provider)
        
        # Map updates
        epic_updates: Dict[str, Any] = {}
        if "name" in updates:
            epic_updates["name"] = updates["name"]
        if "description" in updates:
            epic_updates["description"] = updates["description"]
        if "start_date" in updates:
            from datetime import datetime
            epic_updates["start_date"] = (
                datetime.fromisoformat(updates["start_date"]).date()
                if updates["start_date"]
                else None
            )
        if "end_date" in updates:
            from datetime import datetime
            epic_updates["end_date"] = (
                datetime.fromisoformat(updates["end_date"]).date()
                if updates["end_date"]
                else None
            )
        
        try:
            updated_epic = await provider_instance.update_epic(epic_id, epic_updates)
        except NotImplementedError:
            raise ValueError(f"Epic updates not yet implemented for {provider.provider_type}")
        except Exception as e:
            raise ValueError(str(e))
        
        return {
            "id": str(updated_epic.id),
            "name": updated_epic.name,
            "description": updated_epic.description,
            "status": (
                updated_epic.status.value
                if updated_epic.status and hasattr(updated_epic.status, 'value')
                else str(updated_epic.status) if updated_epic.status else None
            ),
            "priority": (
                updated_epic.priority.value
                if updated_epic.priority and hasattr(updated_epic.priority, 'value')
                else str(updated_epic.priority) if updated_epic.priority else None
            ),
            "start_date": updated_epic.start_date.isoformat() if updated_epic.start_date else None,
            "end_date": updated_epic.end_date.isoformat() if updated_epic.end_date else None,
        }
    
    async def delete_project_epic(self, project_id: str, epic_id: str) -> bool:
        """
        Delete an epic for a specific project.
        
        Args:
            project_id: Project ID in format "provider_id:actual_project_id"
            epic_id: Epic ID
            
        Returns:
            True if deleted successfully
        """
        if ":" not in project_id:
            raise ValueError(f"Invalid project_id format: {project_id}")
        
        parts = project_id.split(":", 1)
        provider_id_str = parts[0]
        
        from uuid import UUID
        try:
            provider_uuid = UUID(provider_id_str)
        except ValueError:
            raise ValueError(f"Invalid provider ID format: {provider_id_str}")
        
        provider = self.db.query(PMProviderConnection).filter(
            PMProviderConnection.id == provider_uuid,
            PMProviderConnection.is_active.is_(True)
        ).first()
        
        if not provider:
            raise ValueError(f"Provider not found: {provider_id_str}")
        
        provider_instance = self._create_provider_instance(provider)
        
        try:
            return await provider_instance.delete_epic(epic_id)
        except NotImplementedError:
            raise ValueError(f"Epic deletion not yet implemented for {provider.provider_type}")
        except Exception as e:
            raise ValueError(str(e))
    
    async def list_project_labels(self, project_id: str) -> List[Dict[str, Any]]:
        """List labels for a specific project"""
        if ":" not in project_id:
            raise ValueError(f"Invalid project_id format: {project_id}")
        
        parts = project_id.split(":", 1)
        provider_id_str = parts[0]
        actual_project_id = parts[1]
        
        from uuid import UUID
        try:
            provider_uuid = UUID(provider_id_str)
        except ValueError:
            raise ValueError(f"Invalid provider ID format: {provider_id_str}")
        
        provider = self.db.query(PMProviderConnection).filter(
            PMProviderConnection.id == provider_uuid,
            PMProviderConnection.is_active.is_(True)
        ).first()
        
        if not provider:
            raise ValueError(f"Provider not found: {provider_id_str}")
        
        provider_instance = self._create_provider_instance(provider)
        
        try:
            labels = await provider_instance.list_labels(project_id=actual_project_id)
        except NotImplementedError:
            raise ValueError(f"Labels not yet implemented for {provider.provider_type}")
        except Exception as e:
            raise ValueError(str(e))
        
        return [
            {
                "id": str(l.id),
                "name": l.name,
                "color": l.color,
                "description": l.description,
            }
            for l in labels
        ]
    
    async def list_project_statuses(
        self,
        project_id: str,
        entity_type: str = "task"
    ) -> List[Dict[str, Any]]:
        """
        Get list of available statuses for an entity type in a project.
        
        This is used by UI/UX to create status columns in Kanban boards.
        
        Args:
            project_id: Project ID in format "provider_id:actual_project_id"
            entity_type: Type of entity ("task", "epic", "project", etc.)
            
        Returns:
            List of status objects with id, name, color, etc.
        """
        provider_instance = self._get_provider_for_project(project_id)
        actual_project_id = (
            project_id.split(":", 1)[1]
            if ":" in project_id
            else project_id
        )

        provider_type = getattr(getattr(provider_instance, "config", None), "provider_type", provider_instance.__class__.__name__)

        try:
            statuses = await provider_instance.list_statuses(
                entity_type=entity_type,
                project_id=actual_project_id
            )
        except NotImplementedError:
            raise ValueError(
                f"Status list not yet implemented for {provider_type}"
            )
        except Exception as e:
            raise ValueError(str(e))

        return statuses
    
    async def list_project_priorities(
        self,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get list of available priorities for a project.
        
        This is used by UI/UX to populate priority dropdowns/selectors.
        
        Args:
            project_id: Project ID in format "provider_id:actual_project_id"
            
        Returns:
            List of priority objects with id, name, color, etc.
        """
        provider_instance = self._get_provider_for_project(project_id)
        actual_project_id = (
            project_id.split(":", 1)[1]
            if ":" in project_id
            else project_id
        )

        provider_type = getattr(getattr(provider_instance, "config", None), "provider_type", provider_instance.__class__.__name__)

        try:
            priorities = await provider_instance.list_priorities(
                project_id=actual_project_id
            )
        except NotImplementedError:
            raise ValueError(
                f"Priority list not yet implemented for {provider_type}"
            )
        except Exception as e:
            raise ValueError(str(e))

        return priorities
    
    async def assign_task_to_epic(self, project_id: str, task_id: str, epic_id: str) -> Dict[str, Any]:
        """
        Assign a task to an epic within a project.
        
        Args:
            project_id: Project ID in format "provider_id:project_key"
            task_id: Task ID to assign
            epic_id: Epic ID to assign to
            
        Returns:
            Updated task dictionary
        """
        provider = self._get_provider_for_project(project_id)
        updated_task = await provider.assign_task_to_epic(task_id, epic_id)
        
        # Get project name for _task_to_dict
        project = await provider.get_project(project_id.split(":")[-1])
        project_name = project.name if project else "Unknown"
        
        return self._task_to_dict(updated_task, project_name)
    
    async def remove_task_from_epic(self, project_id: str, task_id: str) -> Dict[str, Any]:
        """
        Remove a task from its epic.
        
        Args:
            project_id: Project ID in format "provider_id:project_key"
            task_id: Task ID to remove from epic
            
        Returns:
            Updated task dictionary
        """
        provider = self._get_provider_for_project(project_id)
        updated_task = await provider.remove_task_from_epic(task_id)
        
        # Get project name for _task_to_dict
        project = await provider.get_project(project_id.split(":")[-1])
        project_name = project.name if project else "Unknown"
        
        return self._task_to_dict(updated_task, project_name)
    
    async def assign_task_to_sprint(self, project_id: str, task_id: str, sprint_id: str) -> Dict[str, Any]:
        """
        Assign a task to a sprint within a project.
        
        Args:
            project_id: Project ID in format "provider_id:project_key"
            task_id: Task ID to assign
            sprint_id: Sprint ID to assign to
            
        Returns:
            Updated task dictionary
        """
        provider = self._get_provider_for_project(project_id)
        updated_task = await provider.assign_task_to_sprint(task_id, sprint_id)
        
        # Get project name for _task_to_dict
        project = await provider.get_project(project_id.split(":")[-1])
        project_name = project.name if project else "Unknown"
        
        return self._task_to_dict(updated_task, project_name)
    
    async def move_task_to_backlog(self, project_id: str, task_id: str) -> Dict[str, Any]:
        """
        Move a task to the backlog (remove from sprint).
        
        Args:
            project_id: Project ID in format "provider_id:project_key"
            task_id: Task ID to move to backlog
            
        Returns:
            Updated task dictionary
        """
        provider = self._get_provider_for_project(project_id)
        updated_task = await provider.move_task_to_backlog(task_id)
        
        # Get project name for _task_to_dict
        project = await provider.get_project(project_id.split(":")[-1])
        project_name = project.name if project else "Unknown"
        
        return self._task_to_dict(updated_task, project_name)

    async def assign_task_to_user(
        self,
        project_id: str,
        task_id: str,
        assignee_id: Optional[str],
    ) -> Dict[str, Any]:
        """
        Assign a task to a user (assignee).
        """
        provider_instance = self._get_provider_for_project(project_id)
        actual_project_id = (
            project_id.split(":", 1)[1]
            if ":" in project_id
            else project_id
        )

        try:
            updated_task = await provider_instance.update_task(task_id, {"assignee_id": assignee_id})
        except NotImplementedError:
            provider_type = getattr(
                getattr(provider_instance, "config", None),
                "provider_type",
                provider_instance.__class__.__name__,
            )
            raise ValueError(f"Task assignment not yet implemented for {provider_type}")
        except Exception as update_exc:
            raise ValueError(str(update_exc))

        project = await provider_instance.get_project(actual_project_id)
        project_name = project.name if project else "Unknown"

        return self._task_to_dict(updated_task, project_name)

    async def get_project_timeline(self, project_id: str) -> Dict[str, Any]:
        """
        Assemble timeline (sprints + tasks) for a project with scheduling metadata.
        """
        provider_instance = self._get_provider_for_project(project_id)
        actual_project_id = (
            project_id.split(":", 1)[1]
            if ":" in project_id
            else project_id
        )

        provider_type = getattr(
            getattr(provider_instance, "config", None),
            "provider_type",
            provider_instance.__class__.__name__,
        )

        try:
            project = await provider_instance.get_project(actual_project_id)
        except NotImplementedError:
            project = None
        project_name = project.name if project else actual_project_id

        try:
            sprints = await provider_instance.list_sprints(project_id=actual_project_id)
        except NotImplementedError:
            raise ValueError(f"Timeline not yet implemented for {provider_type} provider (missing sprint support)")
        except Exception as exc:
            raise ValueError(str(exc))

        try:
            tasks = await provider_instance.list_tasks(project_id=actual_project_id)
        except NotImplementedError:
            raise ValueError(f"Timeline not yet implemented for {provider_type} provider (missing task support)")
        except Exception as exc:
            raise ValueError(str(exc))

        sprint_lookup: Dict[str, PMSprint] = {}
        scheduled_sprints: List[Dict[str, Any]] = []
        unscheduled_sprints: List[Dict[str, Any]] = []

        def _compute_duration_days(start: Optional[date], end: Optional[date]) -> Optional[int]:
            if not start or not end:
                return None
            delta = (end - start).days
            if delta < 0:
                return None
            return max(delta, 1)

        for sprint in sprints:
            sprint_id = str(sprint.id)
            sprint_lookup[sprint_id] = sprint

            has_start = isinstance(sprint.start_date, date)
            has_end = isinstance(sprint.end_date, date)
            duration_days = _compute_duration_days(sprint.start_date, sprint.end_date)
            is_scheduled = bool(has_start and has_end and duration_days is not None)

            if not has_start and not has_end:
                missing_reason = "missing_start_end"
            elif not has_start:
                missing_reason = "missing_start"
            elif not has_end:
                missing_reason = "missing_end"
            elif duration_days is None:
                missing_reason = "invalid_range"
            else:
                missing_reason = None

            payload = {
                "id": sprint_id,
                "name": sprint.name,
                "start_date": sprint.start_date.isoformat() if has_start else None,
                "end_date": sprint.end_date.isoformat() if has_end else None,
                "status": (
                    sprint.status.value
                    if hasattr(sprint.status, "value")
                    else str(sprint.status) if sprint.status else None
                ),
                "goal": sprint.goal,
                "duration_days": duration_days,
                "is_scheduled": is_scheduled,
                "missing_reason": missing_reason,
            }

            if is_scheduled:
                scheduled_sprints.append(payload)
            else:
                unscheduled_sprints.append(payload)

        assignee_map: Dict[str, str] = {}
        for task in tasks:
            if task.assignee_id and str(task.assignee_id) not in assignee_map:
                try:
                    user = await provider_instance.get_user(str(task.assignee_id))
                except Exception:
                    user = None
                if user:
                    assignee_map[str(task.assignee_id)] = (
                        user.name or user.username or user.email or str(user.id)
                    )

        scheduled_tasks: List[Dict[str, Any]] = []
        unscheduled_tasks: List[Dict[str, Any]] = []

        for task in tasks:
            task_dict = self._task_to_dict(task, project_name)
            sprint_id = str(task.sprint_id) if task.sprint_id else None
            sprint = sprint_lookup.get(sprint_id) if sprint_id else None

            if sprint:
                task_dict["sprint_name"] = sprint.name
                task_dict["sprint_start_date"] = sprint.start_date.isoformat() if sprint.start_date else None
                task_dict["sprint_end_date"] = sprint.end_date.isoformat() if sprint.end_date else None
            else:
                task_dict["sprint_name"] = None
                task_dict["sprint_start_date"] = None
                task_dict["sprint_end_date"] = None

            assignee_id = task_dict.get("assignee_id")
            assigned_to = assignee_map.get(str(assignee_id)) if assignee_id else None
            # Fallback to raw_data extraction if not in map
            if not assigned_to and task.assignee_id:
                assigned_to = self._extract_assignee_name_from_raw_data(task)
                if assigned_to:
                    assignee_map[str(task.assignee_id)] = assigned_to
            task_dict["assigned_to"] = assigned_to

            has_start = bool(task.start_date)
            has_end = bool(task.due_date)
            duration_days = _compute_duration_days(task.start_date, task.due_date)
            is_scheduled = bool(has_start and has_end and duration_days is not None)

            if not has_start and not has_end:
                missing_reason = "missing_start_end"
            elif not has_start:
                missing_reason = "missing_start"
            elif not has_end:
                missing_reason = "missing_end"
            elif duration_days is None:
                missing_reason = "invalid_range"
            else:
                missing_reason = None

            task_dict["duration_days"] = duration_days
            task_dict["is_scheduled"] = is_scheduled
            task_dict["missing_reason"] = missing_reason

            if is_scheduled:
                scheduled_tasks.append(task_dict)
            else:
                unscheduled_tasks.append(task_dict)

        return {
            "project_id": project_id,
            "project_key": actual_project_id,
            "project_name": project_name,
            "sprints": scheduled_sprints,
            "tasks": scheduled_tasks,
            "unscheduled": {
                "sprints": unscheduled_sprints,
                "tasks": unscheduled_tasks,
            },
        }
    
    def _extract_assignee_name_from_raw_data(self, task: PMTask) -> Optional[str]:
        """
        Extract assignee display name from task raw_data as a fallback.
        
        This is useful when get_user() is not implemented or fails.
        Supports JIRA format (fields.assignee.displayName) and other formats.
        """
        if not task.raw_data or not isinstance(task.raw_data, dict):
            return None
        
        assignee_obj = None
        # Check different possible locations for assignee data
        if "fields" in task.raw_data and isinstance(task.raw_data["fields"], dict):
            assignee_obj = task.raw_data["fields"].get("assignee")
        elif "assignee" in task.raw_data:
            assignee_obj = task.raw_data["assignee"]
        
        if assignee_obj and isinstance(assignee_obj, dict):
            # Try different field names for assignee display name
            return (
                assignee_obj.get("displayName") or
                assignee_obj.get("name") or
                assignee_obj.get("emailAddress") or
                assignee_obj.get("email") or
                None
            )
        
        return None

    def _task_to_dict(self, task: PMTask, project_name: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Convert PMTask to dictionary with project_name and project_id"""
        result = {
            "id": str(task.id),
            "title": task.title,
            "description": task.description,
            "status": (
                task.status.value
                if hasattr(task.status, 'value')
                else str(task.status)
            ),
            "priority": (
                task.priority.value
                if hasattr(task.priority, 'value')
                else str(task.priority)
            ),
            "estimated_hours": task.estimated_hours,
            "start_date": (
                task.start_date.isoformat() if task.start_date else None
            ),
            "due_date": (
                task.due_date.isoformat() if task.due_date else None
            ),
            "project_name": project_name,
            "epic_id": str(task.epic_id) if task.epic_id else None,
            "label_ids": [str(lid) for lid in task.label_ids] if task.label_ids else None,
            "sprint_id": str(task.sprint_id) if task.sprint_id else None,
            "assignee_id": str(task.assignee_id) if task.assignee_id else None,
        }
        
        # Add project_id if provided, otherwise use task.project_id
        if project_id:
            result["project_id"] = project_id
        elif task.project_id:
            result["project_id"] = str(task.project_id)
        
        return result

