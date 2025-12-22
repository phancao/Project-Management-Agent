"""
Base classes for analytics calculators.

These abstract base classes provide a consistent interface for all analytics
calculations, making it easy to add new calculators for different domains
(PM analytics, meeting analytics, etc.)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar
from datetime import date as date_type, datetime

from shared.analytics.models import (
    ChartResponse,
    ChartType,
    ChartDataPoint,
    ChartSeries,
    WorkItem,
)

# Type variable for input data
T = TypeVar('T')


class BaseCalculator(ABC, Generic[T]):
    """
    Abstract base class for all analytics calculators.
    
    Each calculator takes some input data and produces a ChartResponse
    with computed metrics and visualizable data.
    """
    
    @property
    @abstractmethod
    def chart_type(self) -> ChartType:
        """The type of chart this calculator produces"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this calculator"""
        pass
    
    @abstractmethod
    async def calculate(self, data: T, **kwargs) -> ChartResponse:
        """
        Perform the calculation and return a chart response.
        
        Args:
            data: Input data for the calculation
            **kwargs: Additional parameters specific to the calculator
            
        Returns:
            ChartResponse with the calculated data
        """
        pass
    
    def _create_series(
        self,
        name: str,
        data_points: List[ChartDataPoint],
        color: Optional[str] = None,
        series_type: Optional[str] = None,
    ) -> ChartSeries:
        """Helper to create a chart series"""
        return ChartSeries(
            name=name,
            data=data_points,
            color=color,
            type=series_type,
        )
    
    def _create_data_point(
        self,
        value: float,
        date: Optional[datetime] = None,
        label: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChartDataPoint:
        """Helper to create a data point"""
        return ChartDataPoint(
            date=date,
            value=value,
            label=label,
            metadata=metadata or {},
        )
    
    def _create_response(
        self,
        title: str,
        series: List[ChartSeries],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChartResponse:
        """Helper to create the final chart response"""
        return ChartResponse(
            chart_type=self.chart_type,
            title=title,
            series=series,
            metadata=metadata or {},
            generated_at=datetime.now(),
        )


class WorkItemCalculator(BaseCalculator[List[WorkItem]]):
    """
    Base class for calculators that operate on work items.
    
    Provides common utilities for filtering and grouping work items.
    """
    
    def filter_by_date_range(
        self,
        items: List[WorkItem],
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
    ) -> List[WorkItem]:
        """Filter work items by date range"""
        filtered = items
        
        if start_date:
            filtered = [
                item for item in filtered 
                if item.created_at.date() >= start_date
            ]
        
        if end_date:
            filtered = [
                item for item in filtered 
                if item.created_at.date() <= end_date
            ]
        
        return filtered
    
    def group_by_status(self, items: List[WorkItem]) -> Dict[str, List[WorkItem]]:
        """Group work items by status"""
        groups: Dict[str, List[WorkItem]] = {}
        for item in items:
            status = item.status.value
            if status not in groups:
                groups[status] = []
            groups[status].append(item)
        return groups
    
    def group_by_assignee(self, items: List[WorkItem]) -> Dict[str, List[WorkItem]]:
        """Group work items by assignee"""
        groups: Dict[str, List[WorkItem]] = {}
        for item in items:
            assignee = item.assigned_to or "Unassigned"
            if assignee not in groups:
                groups[assignee] = []
            groups[assignee].append(item)
        return groups
    
    def group_by_type(self, items: List[WorkItem]) -> Dict[str, List[WorkItem]]:
        """Group work items by type"""
        groups: Dict[str, List[WorkItem]] = {}
        for item in items:
            item_type = item.type.value
            if item_type not in groups:
                groups[item_type] = []
            groups[item_type].append(item)
        return groups
    
    def get_total_story_points(self, items: List[WorkItem]) -> float:
        """Calculate total story points"""
        return sum(item.story_points or 0 for item in items)
    
    def get_total_hours(self, items: List[WorkItem]) -> float:
        """Calculate total estimated hours"""
        return sum(item.estimated_hours or 0 for item in items)


class TimeSeriesCalculator(BaseCalculator[T], Generic[T]):
    """
    Base class for calculators that produce time-series data.
    
    Provides utilities for date range generation and interpolation.
    """
    
    def generate_date_range(
        self,
        start_date: date_type,
        end_date: date_type,
    ) -> List[date_type]:
        """Generate a list of dates between start and end"""
        from datetime import timedelta
        
        dates = []
        current = start_date
        while current <= end_date:
            dates.append(current)
            current += timedelta(days=1)
        return dates
    
    def interpolate_missing(
        self,
        data: Dict[date_type, float],
        dates: List[date_type],
        default: float = 0.0,
    ) -> Dict[date_type, float]:
        """Fill in missing dates with default or interpolated values"""
        result = {}
        for d in dates:
            result[d] = data.get(d, default)
        return result
