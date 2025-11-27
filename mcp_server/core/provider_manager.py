"""
Provider Manager

Manages PM provider lifecycle and instances.
Extracted from MCPPMHandler to separate provider management from business logic.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from ..database.models import PMProviderConnection
from pm_providers.factory import create_pm_provider
from pm_providers.base import BasePMProvider

logger = logging.getLogger(__name__)


class ProviderManager:
    """
    Manages PM provider lifecycle and instances.
    
    Responsibilities:
    - Get active providers from database
    - Create provider instances
    - Cache provider instances
    - Handle provider errors
    """
    
    def __init__(self, db_session: Session, user_id: Optional[str] = None):
        """
        Initialize provider manager.
        
        Args:
            db_session: Database session for querying provider connections
            user_id: Optional user ID to filter providers by user
        """
        self.db = db_session
        self.user_id = user_id
        self._provider_cache: dict[str, BasePMProvider] = {}
        self._last_provider_errors: list[dict] = []
    
    def get_active_providers(self) -> list[PMProviderConnection]:
        """
        Get active PM providers from database.
        
        If user_id is set, only returns providers where created_by = user_id.
        Otherwise, returns all active providers.
        
        Note: Mock providers are excluded - they are UI-only.
        
        Returns:
            List of active PMProviderConnection objects
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
            logger.info(
                "[ProviderManager] Filtering providers by user_id: %s",
                self.user_id
            )
        
        # Exclude mock providers - they are UI-only
        query = query.filter(PMProviderConnection.provider_type != "mock")
        
        providers = query.all()
        logger.info(
            "[ProviderManager] Found %d active provider(s)",
            len(providers)
        )
        return providers
    
    def get_provider_by_id(self, provider_id: str) -> Optional[PMProviderConnection]:
        """
        Get provider connection by ID.
        
        Args:
            provider_id: Provider UUID
        
        Returns:
            PMProviderConnection or None if not found
        """
        if not self.db:
            return None
        
        provider_conn = self.db.query(PMProviderConnection).filter(
            PMProviderConnection.id == provider_id
        ).first()
        
        # Check user access if user_id is set
        if provider_conn and self.user_id:
            if provider_conn.created_by != self.user_id:
                logger.warning(
                    "[ProviderManager] User %s attempted to access provider %s "
                    "owned by %s",
                    self.user_id,
                    provider_id,
                    provider_conn.created_by
                )
                return None
        
        return provider_conn
    
    def create_provider_instance(
        self,
        provider: PMProviderConnection
    ) -> BasePMProvider:
        """
        Create a PM provider instance from database provider connection.
        
        Args:
            provider: PMProviderConnection from database
        
        Returns:
            Configured PM provider instance
        """
        # Check cache first
        cache_key = str(provider.id)
        if cache_key in self._provider_cache:
            logger.debug(
                "[ProviderManager] Using cached provider instance: %s",
                provider.provider_type
            )
            return self._provider_cache[cache_key]
        
        # Prepare API key - handle empty strings and None
        api_key_value = None
        if provider.api_key:
            api_key_str = str(provider.api_key).strip()
            api_key_value = api_key_str if api_key_str else None
        
        api_token_value = None
        if provider.api_token:
            api_token_str = str(provider.api_token).strip()
            api_token_value = api_token_str if api_token_str else None
        
        # Create provider config
        provider_config = {
            "provider_type": provider.provider_type,
            "base_url": provider.base_url,
            "api_key": api_key_value,
            "api_token": api_token_value,
            "username": provider.username,
            "password": provider.password,
        }
        
        logger.info(
            "[ProviderManager] Creating provider instance: %s at %s",
            provider.provider_type,
            provider.base_url
        )
        
        # Create provider instance using factory
        provider_instance = create_pm_provider(provider_config)
        
        # Cache the instance
        self._provider_cache[cache_key] = provider_instance
        
        return provider_instance
    
    async def get_provider(self, provider_id: str) -> BasePMProvider:
        """
        Get provider instance by ID.
        
        This is the main method to use when you need a provider instance.
        
        Args:
            provider_id: Provider UUID
        
        Returns:
            BasePMProvider instance
        
        Raises:
            ValueError: If provider not found or user doesn't have access
        """
        # Get provider connection from database
        provider_conn = self.get_provider_by_id(provider_id)
        
        if not provider_conn:
            raise ValueError(f"Provider {provider_id} not found or access denied")
        
        # Create and return provider instance
        return self.create_provider_instance(provider_conn)
    
    def clear_cache(self) -> None:
        """Clear provider instance cache."""
        self._provider_cache.clear()
        logger.info("[ProviderManager] Provider cache cleared")
    
    def get_last_errors(self) -> list[dict]:
        """Get last provider errors."""
        return self._last_provider_errors
    
    def record_error(self, provider_id: str, error: Exception) -> None:
        """
        Record provider error.
        
        Args:
            provider_id: Provider UUID
            error: Exception that occurred
        """
        self._last_provider_errors.append({
            "provider_id": provider_id,
            "error": str(error),
            "type": type(error).__name__
        })
        
        # Keep only last 10 errors
        if len(self._last_provider_errors) > 10:
            self._last_provider_errors = self._last_provider_errors[-10:]


