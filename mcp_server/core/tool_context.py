"""
Tool Context

Shared context for all MCP tools.
Provides access to core services and managers.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from .provider_manager import ProviderManager
from .analytics_manager import AnalyticsManager
from ..pm_handler import MCPPMHandler

logger = logging.getLogger(__name__)


class ToolContext:
    """
    Shared context for all MCP tools.
    
    Provides access to:
    - Provider manager (for PM provider operations)
    - Analytics manager (for analytics operations)
    - Database session
    - User ID (for user-scoped operations)
    
    This replaces passing multiple parameters to every tool.
    """
    
    def __init__(
        self,
        db_session: Session,
        user_id: Optional[str] = None
    ):
        """
        Initialize tool context.
        
        Args:
            db_session: Database session
            user_id: Optional user ID for user-scoped operations
        """
        self.db = db_session
        self.user_id = user_id
        
        # Initialize managers
        self.provider_manager = ProviderManager(
            db_session=db_session,
            user_id=user_id
        )
        
        self.analytics_manager = AnalyticsManager(
            provider_manager=self.provider_manager
        )
        
        # Initialize PM handler for backward compatibility
        self.pm_handler = MCPPMHandler(
            db_session=db_session,
            user_id=user_id
        )
        
        logger.info(
            "[ToolContext] Initialized%s",
            f" for user {user_id}" if user_id else ""
        )
    
    @classmethod
    def from_pm_handler(cls, pm_handler) -> "ToolContext":
        """
        Create tool context from existing PM handler.
        
        This is for backward compatibility during migration.
        
        Args:
            pm_handler: MCPPMHandler instance
        
        Returns:
            ToolContext instance
        """
        return cls(
            db_session=pm_handler.db,
            user_id=pm_handler.user_id
        )
    
    def clear_caches(self) -> None:
        """Clear all caches."""
        self.provider_manager.clear_cache()
        self.analytics_manager.clear_cache()
        logger.info("[ToolContext] All caches cleared")


