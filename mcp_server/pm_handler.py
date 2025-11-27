"""
MCP Server PM Handler

Independent PM Handler for MCP Server.
This is completely separate from the backend PMHandler.
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .database.models import PMProviderConnection
from pm_providers.factory import create_pm_provider
from pm_providers.base import BasePMProvider

logger = logging.getLogger(__name__)


class MCPPMHandler:
    """
    PM Handler for MCP Server.
    
    This is an independent implementation that uses MCP Server's own database.
    It provides a unified interface for interacting with PM providers.
    
    Renamed from PMHandler to MCPPMHandler to avoid confusion with backend PMHandler.
    """
    
    def __init__(
        self, 
        db_session: Optional[Session] = None,
        user_id: Optional[str] = None
    ):
        """
        Initialize PM handler.
        
        Args:
            db_session: MCP Server database session for querying PM provider connections.
            user_id: Optional user ID to filter providers by user.
                     If provided, only returns providers where created_by = user_id.
        """
        self.db = db_session
        self.user_id = user_id
        self._mode = "multi"  # MCP Server always uses multi-provider mode
        self._last_provider_errors: List[Dict[str, Any]] = []  # Track provider errors
    
    def _find_provider_by_backend_id(self, backend_provider_id: str) -> Optional[PMProviderConnection]:
        """
        Find an MCP server provider that matches a backend provider ID.
        
        Since MCP server and backend have separate databases, we need to match
        providers by their configuration (base_url, provider_type) rather than ID.
        
        This method queries the backend API to get the provider's configuration,
        then finds the matching provider in the MCP server's database.
        
        Args:
            backend_provider_id: Provider ID from the backend database
            
        Returns:
            Matching PMProviderConnection from MCP server, or None if not found
        """
        # For now, we'll search all active providers since we can't easily
        # query the backend API from here. The actual_project_id should be
        # enough to find the right data across providers.
        # 
        # TODO: In the future, we could:
        # 1. Query backend API to get provider config by ID
        # 2. Match by base_url and provider_type
        # 3. Cache the mapping for performance
        logger.info(f"[MCP PMHandler] Looking for provider matching backend ID: {backend_provider_id}")
        return None  # Return None to search all providers
    
    def _get_active_providers(self) -> List[PMProviderConnection]:
        """
        Get active PM providers from MCP Server database.
        
        If user_id is set, only returns providers where created_by = user_id.
        Otherwise, returns all active providers.
        
        NOTE: Mock providers are excluded - they are UI-only and not used in AI/MCP conversations.
        """
        if not self.db:
            return []
        
        query = self.db.query(PMProviderConnection).filter(
            PMProviderConnection.is_active.is_(True)
        )
        
        # Filter by user if user_id is provided
        # Include providers where created_by matches OR created_by is NULL (shared/synced providers)
        if self.user_id:
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    PMProviderConnection.created_by == self.user_id,
                    PMProviderConnection.created_by.is_(None)  # Include synced/shared providers
                )
            )
            logger.info(
                "[MCP PMHandler] Filtering providers by user_id: %s (including shared providers)",
                self.user_id
            )
        
        # Exclude mock providers - they are UI-only and not used in MCP Server
        query = query.filter(PMProviderConnection.provider_type != "mock")
        
        providers = query.all()
        logger.info(
            "[MCP PMHandler] Found %d active provider(s) (mock providers excluded)",
            len(providers)
        )
        return providers
    
    def _create_provider_instance(self, provider: PMProviderConnection) -> BasePMProvider:
        """
        Create a PM provider instance from database provider connection.
        
        Args:
            provider: PMProviderConnection from MCP Server database
            
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
            "[MCP PMHandler] Creating PM connection: "
            "type=%s, username=%s, has_api_token=%s",
            provider.provider_type,
            username_value,
            bool(api_token_value)
        )
        
        # Mock providers are UI-only and should not be used in MCP Server
        # They should be filtered out before reaching this point
        if provider.provider_type == "mock":
            raise ValueError(
                "Mock providers are UI-only and not supported in MCP Server. "
                "Please use real provider types (jira, openproject, etc.)"
            )
        
        return create_pm_provider(
            provider_type=str(provider.provider_type),
            base_url=str(provider.base_url),
            api_key=api_key_value,
            api_token=api_token_value,
            username=username_value,
            organization_id=str(provider.organization_id) if provider.organization_id else None,
            workspace_id=str(provider.workspace_id) if provider.workspace_id else None,
        )
    
    async def list_all_projects(self) -> List[Dict[str, Any]]:
        """
        List all projects from all active providers.
        
        Returns:
            List of projects with provider_id prefix in project.id
        """
        providers = self._get_active_providers()
        
        if not providers:
            return []
        
        all_projects = []
        provider_errors = []  # Track errors per provider
        
        for provider in providers:
            pm_system_name = f"{provider.provider_type} ({provider.base_url})"
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
                logger.info(
                    "[MCP PMHandler] Found %d projects in %s",
                    len(projects),
                    pm_system_name
                )
            except (ValueError, ConnectionError, RuntimeError) as e:
                error_msg = str(e)
                logger.error(
                    "[MCP PMHandler] Error fetching projects from %s: %s",
                    pm_system_name,
                    e,
                    exc_info=True
                )
                # Store error info for reporting
                provider_errors.append({
                    "provider_id": str(provider.id),
                    "provider_name": provider.name or pm_system_name,
                    "provider_type": provider.provider_type,
                    "error": error_msg
                })
                continue
        
        # Store errors in handler for tool to access
        self._last_provider_errors = provider_errors
        
        return all_projects
    
    async def list_all_tasks(
        self,
        project_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all tasks from all active providers.
        
        Args:
            project_id: Optional project ID (with provider_id prefix)
            assignee_id: Optional assignee ID
            status: Optional status filter
        
        Returns:
            List of tasks with provider_id prefix in task.id
        """
        providers = self._get_active_providers()
        
        if not providers:
            return []
        
        all_tasks = []
        
        # Parse project_id if it has provider prefix
        provider_id = None
        actual_project_id = project_id
        if project_id and ":" in project_id:
            provider_id, actual_project_id = project_id.split(":", 1)
        
        for provider in providers:
            pm_system_name = f"{provider.provider_type} ({provider.base_url})"
            # Filter by provider_id if specified
            if provider_id and str(provider.id) != provider_id:
                continue
            
            try:
                provider_instance = self._create_provider_instance(provider)
                
                # Fetch projects for this PM system to build name mapping
                projects = await provider_instance.list_projects()
                project_map = {str(p.id): p.name for p in projects}
                
                # List tasks from the project
                tasks = await provider_instance.list_tasks(
                    project_id=actual_project_id,
                    assignee_id=assignee_id,
                )
                
                # Prefix task ID with provider_id
                for t in tasks:
                    all_tasks.append({
                        "id": f"{provider.id}:{t.id}",
                        "title": t.title,
                        "description": t.description or "",
                        "status": (
                            t.status.value
                            if t.status and hasattr(t.status, 'value')
                            else str(t.status) if t.status else "None"
                        ),
                        "priority": (
                            t.priority.value
                            if t.priority and hasattr(t.priority, 'value')
                            else str(t.priority) if t.priority else "None"
                        ),
                        "assignee": getattr(t, "assignee", None) or getattr(t, "assignee_id", None) or "",
                        "project_id": f"{provider.id}:{t.project_id}",
                        "project_name": project_map.get(str(t.project_id), ""),
                        "provider_id": str(provider.id),
                        "provider_type": provider.provider_type,
                    })
            except (ValueError, ConnectionError, RuntimeError) as e:
                logger.error(
                    "[MCP PMHandler] Error fetching tasks from %s: %s",
                    pm_system_name,
                    e,
                    exc_info=True
                )
                continue
        
        return all_tasks
    
    async def list_all_sprints(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all sprints from all active providers.
        
        Args:
            project_id: Optional project ID (with provider_id prefix)
            status: Optional status filter (active, planned, closed)
        
        Returns:
            List of sprints with provider_id prefix in sprint.id
        """
        providers = self._get_active_providers()
        logger.info(f"[MCP PMHandler] list_all_sprints: project_id={project_id}, status={status}, providers_count={len(providers)}")
        
        if not providers:
            logger.warning("[MCP PMHandler] No active providers found!")
            return []
        
        all_sprints = []
        
        # Parse project_id if it has provider prefix
        provider_id = None
        actual_project_id = project_id
        if project_id and ":" in project_id:
            provider_id, actual_project_id = project_id.split(":", 1)
        
        logger.info(f"[MCP PMHandler] Parsed: provider_id={provider_id}, actual_project_id={actual_project_id}")
        
        # Check if the provider_id matches any MCP server provider
        # If not, it might be a backend provider ID - search all providers
        provider_id_matches_mcp = False
        if provider_id:
            for p in providers:
                if str(p.id) == provider_id:
                    provider_id_matches_mcp = True
                    break
        
        if provider_id and not provider_id_matches_mcp:
            logger.warning(
                f"[MCP PMHandler] Provider ID {provider_id} not found in MCP server. "
                f"This may be a backend provider ID. Searching all providers by project_id={actual_project_id}"
            )
            # Clear provider_id to search all providers
            provider_id = None
        
        for provider in providers:
            provider_name = f"{provider.provider_type} ({provider.base_url})"
            logger.info(f"[MCP PMHandler] Checking PM connection: {provider_name}")
            # Filter by provider_id if it matches an MCP provider
            if provider_id and str(provider.id) != provider_id:
                logger.info(f"[MCP PMHandler] Skipping {provider_name} (doesn't match requested provider)")
                continue
            
            try:
                provider_instance = self._create_provider_instance(provider)
                logger.info(f"[MCP PMHandler] Fetching sprints from {provider_name} for project_id={actual_project_id}")
                
                # List sprints for the project
                # Note: Some PM systems may not support status filter
                try:
                    sprints = await provider_instance.list_sprints(
                        project_id=actual_project_id,
                        status=status,
                    )
                except TypeError as e:
                    if "status" in str(e):
                        # PM system doesn't support status filter, try without it
                        logger.info(f"[MCP PMHandler] {provider_name} doesn't support status filter, retrying without it")
                        sprints = await provider_instance.list_sprints(
                            project_id=actual_project_id,
                        )
                    else:
                        raise
                logger.info(f"[MCP PMHandler] Found {len(sprints)} sprints in project {actual_project_id} from {provider_name}")
                
                # Prefix sprint ID with provider_id
                for s in sprints:
                    all_sprints.append({
                        "id": f"{provider.id}:{s.id}",
                        "name": s.name,
                        "status": (
                            s.status.value
                            if s.status and hasattr(s.status, 'value')
                            else str(s.status) if s.status else "None"
                        ),
                        "start_date": str(s.start_date) if s.start_date else None,
                        "end_date": str(s.end_date) if s.end_date else None,
                        "project_id": f"{provider.id}:{s.project_id}" if s.project_id else None,
                        "provider_id": str(provider.id),
                        "provider_type": provider.provider_type,
                    })
            except (ValueError, ConnectionError, RuntimeError) as e:
                logger.error(
                    "[MCP PMHandler] Error fetching sprints from %s: %s",
                    provider_name,
                    e,
                    exc_info=True
                )
                continue
        
        return all_sprints
    
    async def get_sprint(
        self,
        sprint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific sprint by ID.
        
        Args:
            sprint_id: Sprint ID (with provider_id prefix)
        
        Returns:
            Sprint details or None if not found
        """
        if ":" not in sprint_id:
            raise ValueError("sprint_id must include provider_id prefix (format: provider_id:sprint_id)")
        
        provider_id, actual_sprint_id = sprint_id.split(":", 1)
        
        providers = self._get_active_providers()
        provider = next((p for p in providers if str(p.id) == provider_id), None)
        
        if not provider:
            raise ValueError(f"Provider {provider_id} not found or access denied")
        
        try:
            provider_instance = self._create_provider_instance(provider)
            sprint = await provider_instance.get_sprint(actual_sprint_id)
            
            if not sprint:
                return None
            
            return {
                "id": f"{provider.id}:{sprint.id}",
                "name": sprint.name,
                "status": (
                    sprint.status.value
                    if sprint.status and hasattr(sprint.status, 'value')
                    else str(sprint.status) if sprint.status else "None"
                ),
                "start_date": str(sprint.start_date) if sprint.start_date else None,
                "end_date": str(sprint.end_date) if sprint.end_date else None,
                "project_id": f"{provider.id}:{sprint.project_id}" if sprint.project_id else None,
                "provider_id": str(provider.id),
                "provider_type": provider.provider_type,
            }
        except (ValueError, ConnectionError, RuntimeError) as e:
            logger.error(
                "[MCP PMHandler] Error getting sprint %s: %s",
                sprint_id,
                e,
                exc_info=True
            )
            raise
    
    @classmethod
    def from_db_session(
        cls,
        db_session: Session,
        user_id: Optional[str] = None
    ) -> "MCPPMHandler":
        """
        Create MCPPMHandler instance for multi-provider mode.
        
        Args:
            db_session: MCP Server database session
            user_id: Optional user ID to filter providers by user.
                     If None, aggregates from all active providers.
            
        Returns:
            MCPPMHandler configured for multi-provider mode
        """
        return cls(db_session=db_session, user_id=user_id)
    
    @classmethod
    def from_db_session_and_user(
        cls,
        db_session: Session,
        user_id: str
    ) -> "MCPPMHandler":
        """
        Create MCPPMHandler instance for specific user.
        
        Args:
            db_session: MCP Server database session
            user_id: User ID to filter providers
            
        Returns:
            MCPPMHandler configured for user-scoped multi-provider mode
        """
        return cls(db_session=db_session, user_id=user_id)

