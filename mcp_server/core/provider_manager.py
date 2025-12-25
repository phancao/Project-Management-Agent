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
        
        try:
            # Ensure clean transaction state
            self.db.rollback()
        except Exception:
            pass  # Ignore if no transaction to rollback
        
        try:
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
                    "[ProviderManager] Filtering providers by user_id: %s (including shared providers)",
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
        except Exception as e:
            logger.error(f"[ProviderManager] Error getting active providers: {e}", exc_info=True)
            # Rollback on error to prevent transaction issues
            try:
                self.db.rollback()
            except Exception:
                pass
            # Return empty list on error to prevent system crash
            return []
    
    def get_provider_by_id(self, provider_id: str) -> Optional[PMProviderConnection]:
        """
        Get provider connection by ID.
        
        Args:
            provider_id: Provider UUID (can be MCP provider ID or backend provider ID)
        
        Returns:
            PMProviderConnection or None if not found
        """
        if not self.db:
            return None
        
        # First try to find by MCP provider ID
        provider_conn = self.db.query(PMProviderConnection).filter(
            PMProviderConnection.id == provider_id
        ).first()
        
        # If not found, try to find by backend_provider_id stored in additional_config (for synced providers)
        if not provider_conn:
            # Search in additional_config JSONB field for backend_provider_id
            # Use Python-side filtering instead of SQL function to avoid transaction issues
            try:
                all_providers = self.db.query(PMProviderConnection).all()
                for p in all_providers:
                    if p.additional_config and isinstance(p.additional_config, dict):
                        backend_id = p.additional_config.get('backend_provider_id')
                        if backend_id and str(backend_id) == str(provider_id):
                            provider_conn = p
                            logger.info(
                                "[ProviderManager] Found provider by backend_provider_id=%s (from additional_config), "
                                "mcp_id=%s",
                                provider_id,
                                provider_conn.id
                            )
                            break
            except Exception as e:
                logger.debug(f"[ProviderManager] Error querying by backend_provider_id in additional_config: {e}")
                # Rollback on error to prevent transaction issues
                try:
                    self.db.rollback()
                except Exception:
                    pass
        
        # Check user access if user_id is set
        # Allow access if created_by matches OR created_by is NULL (shared/synced providers)
        if provider_conn and self.user_id:
            if provider_conn.created_by is not None and provider_conn.created_by != self.user_id:
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
        
        logger.info(
            "[ProviderManager] Creating provider instance: %s at %s",
            provider.provider_type,
            provider.base_url
        )
        
        # Create provider instance using factory with keyword arguments
        provider_instance = create_pm_provider(
            provider_type=provider.provider_type,
            base_url=provider.base_url,
            api_key=api_key_value,
            api_token=api_token_value,
            username=provider.username,
        )
        
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
        
        if len(self._last_provider_errors) > 10:
            self._last_provider_errors = self._last_provider_errors[-10:]

    def get_ai_provider(self, provider_id: str) -> Optional[dict]:
        """
        Get AI provider credentials from Main DB.
        
        Args:
            provider_id: 'openai', 'anthropic', etc.
            
        Returns:
            Dict with api_key, or None
        """
        try:
            from ..database.connection import get_main_db_session
            # Import from SHARED database models (mapped to /app/database)
            from database.orm_models import AIProviderAPIKey
            
            # Create a generator
            db_gen = get_main_db_session()
            try:
                db = next(db_gen)
            except RuntimeError:
                logger.warning("Main database not configured, cannot fetch AI provider")
                return None
            
            try:
                provider = db.query(AIProviderAPIKey).filter(
                    AIProviderAPIKey.provider_id == provider_id,
                    AIProviderAPIKey.is_active.is_(True)
                ).first()
                
                if provider:
                    return {
                        "provider_id": provider.provider_id,
                        "api_key": provider.api_key,
                        "base_url": provider.base_url,
                        "model_name": provider.model_name
                    }
                return None
            finally:
                db.close()
                
        except ImportError:
            logger.warning("Could not import AIProviderAPIKey or get_main_db_session.")
            return None
        except Exception as e:
            logger.error(f"Error fetching AI provider {provider_id}: {e}")
            return None


