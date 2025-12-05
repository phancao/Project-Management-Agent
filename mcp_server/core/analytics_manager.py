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
                        or just "project_key" (will use first active provider)
        
        Returns:
            Tuple of (provider_id, actual_project_id)
        """
        if ":" in project_id:
            # Composite ID: "provider_uuid:project_key"
            provider_id, actual_project_id = project_id.split(":", 1)
            # Validate provider_id is UUID format
            try:
                import uuid
                uuid.UUID(provider_id)  # Will raise ValueError if not valid UUID
                return provider_id, actual_project_id
            except ValueError:
                # Not a valid UUID, treat as project_key with no provider
                logger.warning(
                    "[AnalyticsManager] provider_id '%s' in composite ID is not a valid UUID. "
                    "Treating as project_key only.",
                    provider_id
                )
                # Fall through to non-composite handling
        else:
            # Not composite - could be project_key or provider_id
            # Check if it's a valid UUID
            try:
                import uuid
                uuid.UUID(project_id)  # Will raise ValueError if not valid UUID
                # It's a UUID, treat as provider_id (for sprint operations)
                logger.info(
                    "[AnalyticsManager] project_id '%s' is UUID format, treating as provider_id (no project_key)",
                    project_id
                )
                return project_id, ""
            except ValueError:
                # Not a UUID, treat as project_key - use first active provider
                logger.info(
                    "[AnalyticsManager] project_id '%s' is not UUID format, treating as project_key. "
                    "Will use first active provider.",
                    project_id
                )
                # Get first active provider
                active_providers = self.provider_manager.get_active_providers()
                if not active_providers:
                    raise ValueError(
                        f"Cannot determine provider for project_id '{project_id}'. "
                        "No active PM providers found. Please use composite format 'provider_id:project_key'."
                    )
                # Use first active provider
                provider_conn = active_providers[0]
                provider_id = str(provider_conn.id)
                logger.info(
                    "[AnalyticsManager] Using first active provider '%s' for project_key '%s'",
                    provider_id,
                    project_id
                )
                return provider_id, project_id
    
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
            project_id: Project ID (composite "provider_id:project_key")
            sprint_id: Sprint ID (optional, composite or just sprint_key if project_id has provider)
            scope_type: Scope type (story_points, tasks, hours)
        
        Returns:
            Burndown chart data
        """
        # Handle sprint_id format
        if sprint_id:
            if ":" not in sprint_id and ":" in project_id:
                # sprint_id is not composite, construct from project_id's provider
                provider_id = project_id.split(":", 1)[0]
                sprint_id = f"{provider_id}:{sprint_id}"
                logger.info(
                    "[AnalyticsManager] Constructed composite sprint_id from project_id provider: %s",
                    sprint_id
                )
            elif ":" in sprint_id and ":" not in project_id:
                # sprint_id has provider, project_id doesn't - construct project_id
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
            sprint_id: Sprint ID (composite "provider_id:sprint_key" or just "sprint_key" if project_id has provider)
            project_id: Project ID (composite "provider_id:project_key")
        
        Returns:
            Sprint report data
        
        Raises:
            ValueError: If cannot determine provider from either sprint_id or project_id
        """
        # If sprint_id is NOT composite but project_id IS, construct composite sprint_id
        if ":" not in sprint_id:
            if project_id and ":" in project_id:
                # Extract provider from project_id and construct composite sprint_id
                provider_id = project_id.split(":", 1)[0]
                sprint_id = f"{provider_id}:{sprint_id}"
                logger.info(
                    "[AnalyticsManager] Constructed composite sprint_id from project_id provider: %s",
                    sprint_id
                )
            elif project_id and ":" not in project_id:
                # project_id is UUID format, use _parse_project_id to get provider_id
                # _parse_project_id handles UUID format by treating it as provider_id
                try:
                    provider_id, _ = self._parse_project_id(project_id)
                    # If _parse_project_id returns empty actual_project_id, it means project_id was treated as provider_id
                    # But we need to find the actual provider from the project
                    # Try to get service which will resolve the provider
                    try:
                        service, _ = await self.get_service(project_id)
                        # Extract provider_id from the service's adapter
                        if hasattr(service, 'adapter') and hasattr(service.adapter, 'provider'):
                            provider_id = service.adapter.provider.provider_id
                            sprint_id = f"{provider_id}:{sprint_id}"
                            logger.info(
                                "[AnalyticsManager] Constructed composite sprint_id from service adapter provider: %s",
                                sprint_id
                            )
                        else:
                            # Fallback: use provider_id from _parse_project_id
                            sprint_id = f"{provider_id}:{sprint_id}"
                            logger.info(
                                "[AnalyticsManager] Constructed composite sprint_id from parsed provider_id: %s",
                                sprint_id
                            )
                    except Exception as service_error:
                        logger.warning(f"[AnalyticsManager] Failed to get service for project_id '{project_id}': {service_error}")
                        # Fallback: try to get first active provider
                        active_providers = self.provider_manager.get_active_providers()
                        if active_providers:
                            # Get provider_id from connection (stored in additional_config as backend_provider_id)
                            provider_conn = active_providers[0]
                            provider_id = None
                            if provider_conn.additional_config and isinstance(provider_conn.additional_config, dict):
                                provider_id = provider_conn.additional_config.get('backend_provider_id')
                            if not provider_id:
                                # Use connection ID as fallback
                                provider_id = str(provider_conn.id)
                            sprint_id = f"{provider_id}:{sprint_id}"
                            logger.info(
                                "[AnalyticsManager] Constructed composite sprint_id from first active provider: %s",
                                sprint_id
                            )
                        else:
                            raise ValueError(
                                f"Cannot determine provider for sprint_id '{sprint_id}'. "
                                "No active PM providers found. Please use composite format 'provider_id:sprint_key' "
                                "or provide project_id in format 'provider_id:project_key'."
                            )
                except Exception as e:
                    logger.warning(f"[AnalyticsManager] Failed to resolve provider for project_id '{project_id}': {e}")
                    # Final fallback: try to get first active provider
                    try:
                        active_providers = self.provider_manager.get_active_providers()
                        if active_providers:
                            # Get provider_id from connection
                            provider_conn = active_providers[0]
                            provider_id = None
                            if provider_conn.additional_config and isinstance(provider_conn.additional_config, dict):
                                provider_id = provider_conn.additional_config.get('backend_provider_id')
                            if not provider_id:
                                provider_id = str(provider_conn.id)
                            sprint_id = f"{provider_id}:{sprint_id}"
                            logger.info(
                                "[AnalyticsManager] Constructed composite sprint_id from first active provider (final fallback): %s",
                                sprint_id
                            )
                        else:
                            raise ValueError(
                                f"sprint_id must be in composite format 'provider_id:sprint_key', got: '{sprint_id}'. "
                                "Either use composite sprint_id or provide project_id with provider. "
                                "No active PM providers found."
                            )
                    except Exception as fallback_error:
                        raise ValueError(
                            f"sprint_id must be in composite format 'provider_id:sprint_key', got: '{sprint_id}'. "
                            "Either use composite sprint_id or provide project_id with provider. "
                            f"Error: {fallback_error}"
                        )
            else:
                # No project_id provided, try to get from first active provider
                try:
                    active_providers = self.provider_manager.get_active_providers()
                    if active_providers:
                        # Get provider_id from the connection
                        provider_connection = active_providers[0]
                        # provider_id is stored in additional_config or we need to get it from backend_provider_id
                        provider_id = None
                        if hasattr(provider_connection, 'additional_config') and provider_connection.additional_config:
                            provider_id = provider_connection.additional_config.get('backend_provider_id')
                        if not provider_id:
                            # Fallback: use provider connection ID or try to get from provider instance
                            try:
                                provider = await self.provider_manager.get_provider(str(provider_connection.id))
                                if provider and hasattr(provider, 'config') and hasattr(provider.config, 'provider_id'):
                                    provider_id = provider.config.provider_id
                            except Exception:
                                pass
                        if not provider_id:
                            # Last resort: use connection ID as provider_id
                            provider_id = str(provider_connection.id)
                        sprint_id = f"{provider_id}:{sprint_id}"
                        logger.info(
                            "[AnalyticsManager] Constructed composite sprint_id from first active provider (no project_id): %s",
                            sprint_id
                        )
                    else:
                        raise ValueError(
                            f"sprint_id must be in composite format 'provider_id:sprint_key', got: '{sprint_id}'. "
                            "Either use composite sprint_id or provide project_id with provider. "
                            "No active PM providers found."
                        )
                except Exception as e:
                    raise ValueError(
                        f"sprint_id must be in composite format 'provider_id:sprint_key', got: '{sprint_id}'. "
                        "Either use composite sprint_id or provide project_id with provider. "
                        f"Error: {e}"
                    )
        
        # Extract provider_id from sprint_id
        provider_id = sprint_id.split(":", 1)[0]
        
        # Determine final project_id for service lookup
        if project_id and ":" in project_id:
            # Use provided composite project_id
            pass
        elif project_id and ":" not in project_id:
            # project_id is just provider_id, use sprint's provider
            logger.info(
                "[AnalyticsManager] project_id '%s' is provider-only, using provider from sprint_id: %s",
                project_id, provider_id
            )
            project_id = provider_id
        else:
            # No project_id, use provider from sprint_id
            project_id = provider_id
            logger.info(
                "[AnalyticsManager] Using provider_id from sprint_id: %s",
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

    async def get_cfd_chart(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        days: int = 30
    ) -> dict:
        """
        Get Cumulative Flow Diagram (CFD) data.
        
        Args:
            project_id: Project ID
            sprint_id: Optional sprint ID to filter by
            days: Number of days to include (default: 30)
        
        Returns:
            CFD chart data with:
            - dates: List of dates
            - statuses: Dict of status -> count per date
            - wip_analysis: Work in progress analysis
        """
        # Handle sprint_id format
        if sprint_id and ":" not in sprint_id and ":" in project_id:
            provider_id = project_id.split(":", 1)[0]
            sprint_id = f"{provider_id}:{sprint_id}"
        
        service, actual_project_id = await self.get_service(project_id)
        return await service.get_cfd_chart(
            project_id=actual_project_id,
            sprint_id=sprint_id,
            days_back=days  # Service uses days_back parameter
        )
    
    async def get_cycle_time_chart(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        days: int = 30
    ) -> dict:
        """
        Get cycle time analysis data.
        
        Args:
            project_id: Project ID
            sprint_id: Optional sprint ID to filter by
            days: Number of days to include (default: 30)
        
        Returns:
            Cycle time data with:
            - average: Average cycle time in days
            - median: Median cycle time (50th percentile)
            - p85: 85th percentile (use for commitments)
            - p95: 95th percentile (outliers above this)
            - items: List of completed items with cycle times
        """
        if sprint_id and ":" not in sprint_id and ":" in project_id:
            provider_id = project_id.split(":", 1)[0]
            sprint_id = f"{provider_id}:{sprint_id}"
        
        service, actual_project_id = await self.get_service(project_id)
        return await service.get_cycle_time_chart(
            project_id=actual_project_id,
            sprint_id=sprint_id,
            days_back=days  # Service uses days_back parameter
        )
    
    async def get_work_distribution_chart(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        group_by: str = "assignee"
    ) -> dict:
        """
        Get work distribution analysis.
        
        Args:
            project_id: Project ID
            sprint_id: Optional sprint ID to filter by
            group_by: Grouping dimension (assignee, status, priority, type)
        
        Returns:
            Work distribution data with:
            - groups: Dict of group_name -> task count
            - total: Total task count
            - distribution: Percentage distribution
        """
        if sprint_id and ":" not in sprint_id and ":" in project_id:
            provider_id = project_id.split(":", 1)[0]
            sprint_id = f"{provider_id}:{sprint_id}"
        
        service, actual_project_id = await self.get_service(project_id)
        return await service.get_work_distribution_chart(
            project_id=actual_project_id,
            sprint_id=sprint_id,
            dimension=group_by  # Service uses dimension parameter
        )
    
    async def get_issue_trend_chart(
        self,
        project_id: str,
        days: int = 30
    ) -> dict:
        """
        Get issue trend analysis (created vs resolved).
        
        Args:
            project_id: Project ID
            days: Number of days to analyze (default: 30)
        
        Returns:
            Issue trend data with:
            - dates: List of dates
            - created: Issues created per day
            - resolved: Issues resolved per day
            - net_change: Net change per day
            - cumulative: Cumulative backlog size
        """
        service, actual_project_id = await self.get_service(project_id)
        return await service.get_issue_trend_chart(
            project_id=actual_project_id,
            days_back=days  # Service uses days_back parameter
        )


