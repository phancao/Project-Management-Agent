"""
Tool Context

Shared context for all MCP tools.
Provides access to core services and managers.
"""

import logging
import os
from typing import Optional
from sqlalchemy.orm import Session

from .provider_manager import ProviderManager
from .analytics_manager import AnalyticsManager
from pm_service.client import AsyncPMServiceClient

logger = logging.getLogger(__name__)


class ToolContext:
    """
    Shared context for all MCP tools.
    
    Provides access to:
    - Provider manager (for PM provider operations)
    - Analytics manager (for analytics operations)
    - PM Service client (for API calls to PM Service)
    - Database session
    - User ID (for user-scoped operations)
    
    This replaces passing multiple parameters to every tool.
    """
    
    def __init__(
        self,
        db_session: Session,
        user_id: Optional[str] = None,
        pm_service_url: Optional[str] = None
    ):
        """
        Initialize tool context.
        
        Args:
            db_session: Database session
            user_id: Optional user ID for user-scoped operations
            pm_service_url: Optional PM Service URL (default from env)
        """
        self.db = db_session
        self.user_id = user_id
        
        # Initialize PM Service client
        self._pm_service_url = pm_service_url or os.environ.get(
            "PM_SERVICE_URL", "http://localhost:8001"
        )
        self._pm_service_client: Optional[AsyncPMServiceClient] = None
        
        # Initialize managers
        self.provider_manager = ProviderManager(
            db_session=db_session,
            user_id=user_id
        )
        
        self.analytics_manager = AnalyticsManager(
            provider_manager=self.provider_manager
        )
        
        logger.info(
            "[ToolContext] Initialized%s (PM Service: %s)",
            f" for user {user_id}" if user_id else "",
            self._pm_service_url
        )
    
    @property
    def pm_service(self) -> AsyncPMServiceClient:
        """
        Get PM Service client.
        
        Returns:
            AsyncPMServiceClient instance
        """
        if self._pm_service_client is None:
            self._pm_service_client = AsyncPMServiceClient(base_url=self._pm_service_url)
        return self._pm_service_client
    
    @classmethod
    def from_db_session(
        cls,
        db_session: Session,
        user_id: Optional[str] = None
    ) -> "ToolContext":
        """
        Create tool context from database session.
        Loads PM Service URL from provider configuration if available.
        
        Args:
            db_session: Database session
            user_id: Optional user ID
        
        Returns:
            ToolContext instance
        """
        # Load PM Service URL from provider configuration (required)
        from pm_service.handlers import PMHandler
        handler = PMHandler(db_session, user_id=user_id)
        pm_service_url = handler.get_pm_service_url()
        logger.info(f"Loaded PM Service URL from provider config: {pm_service_url}")
        
        return cls(db_session=db_session, user_id=user_id, pm_service_url=pm_service_url)
    
    def clear_caches(self) -> None:
        """Clear all caches."""
        self.provider_manager.clear_cache()
        self.analytics_manager.clear_cache()
        logger.info("[ToolContext] All caches cleared")


