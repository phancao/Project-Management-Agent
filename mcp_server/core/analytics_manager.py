"""
Analytics Manager

Integrates analytics service with provider manager.
Provides a clean interface for analytics operations across all PM providers.
"""

import logging
from typing import Optional

from .provider_manager import ProviderManager
from src.analytics.service import AnalyticsService
from src.analytics.adapters.pm_adapter import PMProviderAnalyticsAdapter

logger = logging.getLogger(__name__)


class AnalyticsManager:
    """
    Manages analytics services for projects.
    
    Responsibilities:
    - Create analytics services for projects
    - Cache analytics services
    - Manage analytics adapters
    - Parse composite project IDs
    
    This replaces the custom _get_analytics_service() logic that was
    duplicated in every analytics tool.
    """
    
    def __init__(self, provider_manager: ProviderManager):
        """
        Initialize analytics manager.
        
        Args:
            provider_manager: Provider manager instance
        """
        self.provider_manager = provider_manager
        self._service_cache: dict[str, AnalyticsService] = {}
    
    async def get_service(self, project_id: str) -> tuple[AnalyticsService, str]:
        """
        Get analytics service for a project.
        
        Args:
            project_id: Project ID (may be composite "provider_id:project_key")
        
        Returns:
            Tuple of (AnalyticsService instance, actual_project_id)
        
        Raises:
            ValueError: If provider not found or no active providers
        """
        # Parse composite project ID
        provider_id, actual_project_id = self._parse_project_id(project_id)
        
        # Check cache
        cache_key = f"{provider_id}:{actual_project_id}"
        if cache_key in self._service_cache:
            logger.debug(
                "[AnalyticsManager] Using cached analytics service for %s",
                cache_key
            )
            return self._service_cache[cache_key], actual_project_id
        
        logger.info(
            "[AnalyticsManager] Creating analytics service for project_id=%s, "
            "provider_id=%s, actual_project_id=%s",
            project_id,
            provider_id,
            actual_project_id
        )
        
        # Get provider instance from provider manager
        provider = await self.provider_manager.get_provider(provider_id)
        
        logger.info(
            "[AnalyticsManager] Got provider: %s at %s",
            provider.config.provider_type,
            provider.config.base_url
        )
        
        # Create analytics adapter
        adapter = PMProviderAnalyticsAdapter(provider)
        
        # Create analytics service
        service = AnalyticsService(adapter=adapter)
        
        # Cache service
        self._service_cache[cache_key] = service
        
        logger.info(
            "[AnalyticsManager] Created analytics service for project %s",
            actual_project_id
        )
        
        return service, actual_project_id
    
    def _parse_project_id(self, project_id: str) -> tuple[str, str]:
        """
        Parse composite project ID into provider_id and project_key.
        
        Args:
            project_id: Project ID - either composite "provider_id:project_key" 
                        or just "provider_id" (for sprint operations where project_key
                        is extracted from sprint)
        
        Returns:
            Tuple of (provider_id, actual_project_id)
            If project_id is provider-only, actual_project_id will be empty string
        """
        if ":" in project_id:
            # Composite ID: "provider_uuid:project_key"
            provider_id, actual_project_id = project_id.split(":", 1)
            return provider_id, actual_project_id
        else:
            # Provider-only ID (valid for sprint operations)
            # The actual_project_id will be determined from sprint info
            logger.info(
                "[AnalyticsManager] project_id '%s' is provider-only (no project_key)",
                project_id
            )
            return project_id, ""
    
    def clear_cache(self) -> None:
        """Clear analytics service cache."""
        self._service_cache.clear()
        logger.info("[AnalyticsManager] Analytics service cache cleared")
    
    async def get_burndown_chart(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        scope_type: str = "story_points"
    ) -> dict:
        """
        Get burndown chart data.
        
        Convenience method that combines get_service() and service call.
        
        Args:
            project_id: Project ID (may be composite "provider_id:project_key")
            sprint_id: Sprint ID (optional, may be composite "provider_id:sprint_key")
            scope_type: Scope type (story_points, tasks, hours)
        
        Returns:
            Burndown chart data
        """
        # If sprint_id has provider info and project_id doesn't, use sprint's provider
        if sprint_id and ":" in sprint_id and ":" not in project_id:
            provider_id = sprint_id.split(":", 1)[0]
            project_id = f"{provider_id}:{project_id}"
            logger.info(
                "[AnalyticsManager] Constructed project_id from sprint provider: %s",
                project_id
            )
        
        service, actual_project_id = await self.get_service(project_id)
        return await service.get_burndown_chart(
            project_id=actual_project_id,
            sprint_id=sprint_id,
            scope_type=scope_type
        )
    
    async def get_velocity_chart(
        self,
        project_id: str,
        num_sprints: int = 6
    ) -> dict:
        """
        Get velocity chart data.
        
        Args:
            project_id: Project ID
            num_sprints: Number of sprints to include
        
        Returns:
            Velocity chart data
        """
        service, actual_project_id = await self.get_service(project_id)
        return await service.get_velocity_chart(
            project_id=actual_project_id,
            sprint_count=num_sprints  # service uses sprint_count parameter
        )
    
    async def get_sprint_report(
        self,
        sprint_id: str,
        project_id: Optional[str] = None
    ) -> dict:
        """
        Get sprint report data.
        
        Args:
            sprint_id: Sprint ID (MUST be composite "provider_id:sprint_key")
            project_id: Project ID (optional, extracted from sprint_id if not provided)
        
        Returns:
            Sprint report data
        
        Raises:
            ValueError: If sprint_id is not in composite format and project_id is not provided
        """
        # Ensure we have provider info
        if ":" not in sprint_id:
            raise ValueError(
                f"sprint_id must be in composite format 'provider_id:sprint_key', got: '{sprint_id}'. "
                "Please use composite sprint_id format."
            )
        
        # Extract provider_id from sprint_id
        provider_id = sprint_id.split(":", 1)[0]
        
        # If project_id is provided but doesn't have ":", treat it as provider_id only
        # and use provider from sprint_id
        if project_id and ":" not in project_id:
            # project_id is just provider_id, use sprint's provider
            logger.info(
                "[AnalyticsManager] project_id '%s' is provider-only, using provider from sprint_id: %s",
                project_id, provider_id
            )
            project_id = provider_id
        elif not project_id:
            project_id = provider_id
            logger.info(
                "[AnalyticsManager] Extracted provider_id from sprint_id: %s",
                provider_id
            )
        
        service, actual_project_id = await self.get_service(project_id)
        return await service.get_sprint_report(
            sprint_id=sprint_id,
            project_id=actual_project_id
        )
    
    async def get_project_summary(
        self,
        project_id: str
    ) -> dict:
        """
        Get project summary/health data.
        
        Args:
            project_id: Project ID
        
        Returns:
            Project summary data
        """
        service, actual_project_id = await self.get_service(project_id)
        return await service.get_project_summary(
            project_id=actual_project_id
        )


