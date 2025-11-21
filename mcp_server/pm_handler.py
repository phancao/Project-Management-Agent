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
from pm_providers.models import PMTask, PMProject, PMSprint

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
        if self.user_id:
            query = query.filter(
                PMProviderConnection.created_by == self.user_id
            )
            logger.info(f"[MCP PMHandler] Filtering providers by user_id: {self.user_id}")
        
        # Exclude mock providers - they are UI-only and not used in MCP Server
        query = query.filter(PMProviderConnection.provider_type != "mock")
        
        providers = query.all()
        logger.info(f"[MCP PMHandler] Found {len(providers)} active provider(s) (mock providers excluded)")
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
            f"[MCP PMHandler._create_provider_instance] Creating provider: "
            f"type={provider.provider_type}, "
            f"username={username_value}, "
            f"has_api_token={bool(api_token_value)}"
        )
        
        # Mock providers are UI-only and should not be used in MCP Server
        # They should be filtered out before reaching this point
        if provider.provider_type == "mock":
            raise ValueError(
                "Mock providers are UI-only and not supported in MCP Server. "
                "Please use real provider types (jira, openproject, etc.)"
            )
        
        return create_pm_provider(
            provider_type=provider.provider_type,
            base_url=provider.base_url,
            api_key=api_key_value,
            api_token=api_token_value,
            username=username_value,
            organization_id=provider.organization_id,
            workspace_id=provider.workspace_id,
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
                    f"[MCP PMHandler] Successfully retrieved {len(projects)} projects "
                    f"from provider {provider.id} ({provider.provider_type})"
                )
            except Exception as e:
                error_msg = str(e)
                logger.error(
                    f"[MCP PMHandler] Error listing projects from provider {provider.id}: {e}",
                    exc_info=True
                )
                # Store error info for reporting
                provider_errors.append({
                    "provider_id": str(provider.id),
                    "provider_name": provider.name or f"{provider.provider_type} ({provider.base_url})",
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
        status: Optional[str] = None,
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
            # Filter by provider_id if specified
            if provider_id and str(provider.id) != provider_id:
                continue
            
            try:
                provider_instance = self._create_provider_instance(provider)
                
                # Fetch projects for this provider to build name mapping
                projects = await provider_instance.list_projects()
                project_map = {str(p.id): p.name for p in projects}
                
                # List tasks
                tasks = await provider_instance.list_tasks(
                    project_id=actual_project_id,
                    assignee_id=assignee_id,
                    status=status,
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
                        "assignee": t.assignee or "",
                        "project_id": f"{provider.id}:{t.project_id}",
                        "project_name": project_map.get(str(t.project_id), ""),
                        "provider_id": str(provider.id),
                        "provider_type": provider.provider_type,
                    })
            except Exception as e:
                logger.error(
                    f"[MCP PMHandler] Error listing tasks from provider {provider.id}: {e}",
                    exc_info=True
                )
                continue
        
        return all_tasks
    
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

