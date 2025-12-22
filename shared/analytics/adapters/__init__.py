"""
Base adapter interface for analytics data sources.

Adapters transform data from different sources (PM providers, meeting systems)
into the standardized format expected by calculators.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar
from datetime import date as date_type

from shared.analytics.models import (
    WorkItem,
    SprintData,
    TaskTransition,
)

# Type variable for the source data type
SourceT = TypeVar('SourceT')


class BaseAnalyticsAdapter(ABC, Generic[SourceT]):
    """
    Abstract base class for analytics data adapters.
    
    Adapters are responsible for fetching and transforming data from
    external sources into the standard analytics models.
    """
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the data source (e.g., 'openproject', 'jira', 'meeting')"""
        pass
    
    @abstractmethod
    async def get_work_items(
        self,
        source: SourceT,
        project_id: Optional[str] = None,
        sprint_id: Optional[str] = None,
        **kwargs
    ) -> List[WorkItem]:
        """
        Fetch work items from the source.
        
        Args:
            source: The data source (provider, connection, etc.)
            project_id: Optional project filter
            sprint_id: Optional sprint filter
            **kwargs: Source-specific parameters
            
        Returns:
            List of standardized WorkItem objects
        """
        pass
    
    @abstractmethod
    async def get_sprint_data(
        self,
        source: SourceT,
        sprint_id: str,
        **kwargs
    ) -> Optional[SprintData]:
        """
        Fetch complete sprint data.
        
        Args:
            source: The data source
            sprint_id: Sprint identifier
            **kwargs: Source-specific parameters
            
        Returns:
            SprintData or None if not found
        """
        pass
    
    async def get_task_transitions(
        self,
        source: SourceT,
        task_id: str,
        **kwargs
    ) -> List[TaskTransition]:
        """
        Fetch task status transitions history.
        
        Override if the source supports transition history.
        Default returns empty list.
        """
        return []
    
    async def get_sprints_for_project(
        self,
        source: SourceT,
        project_id: str,
        **kwargs
    ) -> List[SprintData]:
        """
        Fetch all sprints for a project.
        
        Override for project-level sprint listing.
        Default returns empty list.
        """
        return []


class CachingAdapter(BaseAnalyticsAdapter[SourceT], Generic[SourceT]):
    """
    Adapter with built-in caching support.
    
    Subclass this if your data source is expensive to query.
    """
    
    def __init__(self, cache_ttl_seconds: int = 300):
        """
        Initialize with cache TTL.
        
        Args:
            cache_ttl_seconds: Cache time-to-live in seconds (default 5 min)
        """
        self._cache: Dict[str, Any] = {}
        self._cache_times: Dict[str, float] = {}
        self._cache_ttl = cache_ttl_seconds
    
    def _get_cache_key(self, *args, **kwargs) -> str:
        """Generate a cache key from arguments"""
        import hashlib
        import json
        
        key_data = json.dumps({
            'args': [str(a) for a in args],
            'kwargs': {k: str(v) for k, v in sorted(kwargs.items())}
        }, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if a cache entry is still valid"""
        import time
        
        if key not in self._cache_times:
            return False
        
        age = time.time() - self._cache_times[key]
        return age < self._cache_ttl
    
    def _set_cache(self, key: str, value: Any) -> None:
        """Set a cache entry"""
        import time
        
        self._cache[key] = value
        self._cache_times[key] = time.time()
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """Get a cache entry if valid"""
        if self._is_cache_valid(key):
            return self._cache.get(key)
        return None
    
    def clear_cache(self) -> None:
        """Clear all cached data"""
        self._cache.clear()
        self._cache_times.clear()
