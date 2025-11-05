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
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session

from database.orm_models import PMProviderConnection
from src.pm_providers.factory import create_pm_provider
from src.pm_providers.base import BasePMProvider
from src.pm_providers.builder import build_pm_provider
from src.pm_providers.models import PMTask, PMProject

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
        single_provider: Optional[BasePMProvider] = None
    ):
        """
        Initialize PM handler.
        
        Args:
            db_session: Database session for querying PM provider connections.
                       Required for multi-provider mode.
            single_provider: Optional single provider instance to use.
                            If provided, operates in single-provider mode.
                            If None, operates in multi-provider mode using db_session.
        """
        self.db = db_session
        self.single_provider = single_provider
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
        db_session: Session
    ) -> "PMHandler":
        """
        Create PMHandler instance for multi-provider mode.
        
        This aggregates data from all active providers in the database.
        Useful for API endpoints that need to show data from all providers.
        
        Args:
            db_session: Database session for querying providers
            
        Returns:
            PMHandler configured for multi-provider mode
        """
        return cls(db_session=db_session)
    
    def _get_active_providers(self) -> List[PMProviderConnection]:
        """Get all active PM providers from database"""
        if not self.db:
            return []
        return self.db.query(PMProviderConnection).filter(
            PMProviderConnection.is_active.is_(True)
        ).all()
    
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
        
        return create_pm_provider(
            provider_type=str(provider.provider_type),
            base_url=str(provider.base_url),
            api_key=api_key_value,
            api_token=api_token_value,
            username=(
                str(provider.username).strip()
                if provider.username
                else None
            ),
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
                    
                    if task_project_id:
                        # Try with provider prefix first
                        prefixed_id = f"{provider.id}:{task_project_id}"
                        if prefixed_id in all_projects_map:
                            project_name = all_projects_map[prefixed_id]
                        elif task_project_id in all_projects_map:
                            project_name = all_projects_map[task_project_id]
                    
                    all_tasks.append(self._task_to_dict(task, project_name))
                        
            except Exception as provider_error:
                logger.warning(
                    f"Failed to fetch tasks from provider "
                    f"{provider.id} ({provider.provider_type}): {provider_error}"
                )
                continue
        
        return all_tasks
    
    async def list_my_tasks(self) -> List[Dict[str, Any]]:
        """
        List tasks assigned to current user.
        
        In single-provider mode: Returns tasks from the single provider.
        In multi-provider mode: Returns tasks from all active providers.
        
        Returns:
            List of tasks assigned to the current user with project_name mapped
        """
        if self._mode == "single":
            # Single provider mode
            if not self.single_provider:
                return []
            
            current_user = await self.single_provider.get_current_user()
            if not current_user:
                return []
            
            projects = await self.single_provider.list_projects()
            project_map = {p.id: p.name for p in projects}
            
            try:
                tasks = await self.single_provider.list_tasks(
                    assignee_id=current_user.id
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
            
            return [
                self._task_to_dict(
                    task,
                    project_map.get(task.project_id, "Unknown")
                )
                for task in tasks
            ]
        
        # Multi-provider mode
        providers = self._get_active_providers()
        
        if not providers:
            return []
        
        all_tasks = []
        all_projects_map = {}  # Map project_id to project_name across all providers
        
        for provider in providers:
            try:
                provider_instance = self._create_provider_instance(provider)
                
                # Get current user for this provider
                try:
                    logger.info(
                        f"Attempting to get current user for provider "
                        f"{provider.id} ({provider.provider_type})..."
                    )
                    current_user = await provider_instance.get_current_user()
                    if not current_user:
                        logger.warning(
                            f"Cannot determine current user for provider "
                            f"{provider.id} ({provider.provider_type}). "
                            f"get_current_user() returned None. "
                            f"Skipping my tasks for this provider."
                        )
                        continue
                    else:
                        logger.info(
                            f"Successfully retrieved current user for provider "
                            f"{provider.id} ({provider.provider_type}): "
                            f"id={current_user.id}, name={current_user.name}"
                        )
                except Exception as user_error:
                    logger.warning(
                        f"Failed to get current user for provider "
                        f"{provider.id} ({provider.provider_type}): {user_error}",
                        exc_info=True
                    )
                    continue
                
                # Fetch projects for this provider to build name mapping
                projects = await provider_instance.list_projects()
                for p in projects:
                    # Store with provider_id prefix to ensure uniqueness
                    prefixed_id = f"{provider.id}:{p.id}"
                    all_projects_map[prefixed_id] = p.name
                    # Also store without prefix for backward compatibility
                    all_projects_map[p.id] = p.name
                
                # Fetch tasks assigned to current user
                all_provider_tasks = []
                try:
                    tasks = await provider_instance.list_tasks(
                        assignee_id=current_user.id
                    )
                    all_provider_tasks = tasks
                except Exception as e:
                    error_msg = str(e).lower()
                    # If JIRA requires project-specific queries, fetch per project
                    if "unbounded" in error_msg or "search restriction" in error_msg:
                        logger.info(
                            f"Provider {provider.provider_type} requires project-specific queries. "
                            f"Fetching my tasks per project..."
                        )
                        # Fetch tasks for each project with assignee filter
                        for project in projects:
                            try:
                                project_tasks = await provider_instance.list_tasks(
                                    project_id=project.id,
                                    assignee_id=current_user.id
                                )
                                all_provider_tasks.extend(project_tasks)
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
                
                # Add tasks with project_name mapping
                for task in tasks:
                    task_project_id = task.project_id
                    project_name = "Unknown"
                    
                    if task_project_id:
                        # Try with provider prefix first
                        prefixed_id = f"{provider.id}:{task_project_id}"
                        if prefixed_id in all_projects_map:
                            project_name = all_projects_map[prefixed_id]
                        elif task_project_id in all_projects_map:
                            project_name = all_projects_map[task_project_id]
                    
                    all_tasks.append(self._task_to_dict(task, project_name))
                        
            except Exception as provider_error:
                logger.warning(
                    f"Failed to fetch my tasks from provider "
                    f"{provider.id} ({provider.provider_type}): {provider_error}"
                )
                continue
        
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
        if ":" not in project_id:
            raise ValueError(f"Invalid project_id format: {project_id}. Expected format: provider_id:project_id")
        
        parts = project_id.split(":", 1)
        provider_id_str = parts[0]
        actual_project_id = parts[1]
        
        from uuid import UUID
        try:
            provider_uuid = UUID(provider_id_str)
        except ValueError:
            raise ValueError(f"Invalid provider ID format: {provider_id_str}")
        
        # Get provider from database
        provider = self.db.query(PMProviderConnection).filter(
            PMProviderConnection.id == provider_uuid,
            PMProviderConnection.is_active.is_(True)
        ).first()
        
        if not provider:
            raise ValueError(f"Provider not found: {provider_id_str}")
        
        logger.info(
            f"Using provider: id={provider.id}, "
            f"type={provider.provider_type}, "
            f"base_url={provider.base_url}, "
            f"project_id={actual_project_id}"
        )
        
        # Create provider instance
        provider_instance = self._create_provider_instance(provider)
        
        # Fetch projects for name mapping
        projects = await provider_instance.list_projects()
        project_map = {p.id: p.name for p in projects}
        
        # Fetch tasks
        try:
            logger.info(
                "=" * 80
            )
            logger.info(
                "CALLING PROVIDER list_tasks: "
                "provider=%s, project_id=%s, actual_project_id=%s",
                provider.provider_type, project_id, actual_project_id
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
                f"{provider.provider_type}"
            )
            raise ValueError(
                f"list_tasks is not yet implemented for "
                f"{provider.provider_type} provider"
            )
        except Exception as list_error:
            error_msg = str(list_error)
            logger.error(
                f"Failed to list tasks for project {actual_project_id} "
                f"from provider {provider_id_str} "
                f"(type: {provider.provider_type}): {error_msg}"
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
                except Exception:
                    pass
        
        # Map project names
        project_name = project_map.get(actual_project_id, "Unknown")
        
        # Convert tasks to dict with assignee names
        result = []
        for task in tasks:
            task_dict = self._task_to_dict(task, project_name)
            task_dict["assigned_to"] = (
                assignee_map.get(task.assignee_id)
                if task.assignee_id
                else None
            )
            result.append(task_dict)
        
        return result
    
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
        if ":" not in project_id:
            raise ValueError(f"Invalid project_id format: {project_id}. Expected format: provider_id:project_id")
        
        parts = project_id.split(":", 1)
        provider_id_str = parts[0]
        actual_project_id = parts[1]
        
        from uuid import UUID
        try:
            provider_uuid = UUID(provider_id_str)
        except ValueError:
            raise ValueError(f"Invalid provider ID format: {provider_id_str}")
        
        # Get provider from database
        provider = self.db.query(PMProviderConnection).filter(
            PMProviderConnection.id == provider_uuid,
            PMProviderConnection.is_active.is_(True)
        ).first()
        
        if not provider:
            raise ValueError(f"Provider not found: {provider_id_str}")
        
        # Create provider instance
        provider_instance = self._create_provider_instance(provider)
        
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
            epics = await provider_instance.list_epics(project_id=actual_project_id)
        except NotImplementedError:
            raise ValueError(f"Epics not yet implemented for {provider.provider_type}")
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
        from src.pm_providers.models import PMEpic
        
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
    ) -> List[str]:
        """
        Get list of available statuses for an entity type in a project.
        
        This is used by UI/UX to create status columns in Kanban boards.
        
        Args:
            project_id: Project ID in format "provider_id:actual_project_id"
            entity_type: Type of entity ("task", "epic", "project", etc.)
            
        Returns:
            Ordered list of status names
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
        
        try:
            statuses = await provider_instance.list_statuses(
                entity_type=entity_type,
                project_id=actual_project_id
            )
        except NotImplementedError:
            raise ValueError(
                f"Status list not yet implemented for {provider.provider_type}"
            )
        except Exception as e:
            raise ValueError(str(e))
        
        return statuses
    
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
    
    def _task_to_dict(self, task: PMTask, project_name: str) -> Dict[str, Any]:
        """Convert PMTask to dictionary with project_name"""
        return {
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
        }

