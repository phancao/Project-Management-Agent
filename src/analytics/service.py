"""
Analytics service - main entry point for chart generation.

Orchestrates data fetching, calculation, and caching for all chart types.
"""

from typing import Optional, Literal, Dict, Any
from datetime import datetime, timedelta
import asyncio
import logging

from src.analytics.models import ChartResponse, SprintReport

logger = logging.getLogger(__name__)
from src.analytics.mock_data import MockDataGenerator
from src.analytics.calculators.burndown import BurndownCalculator
from src.analytics.calculators.velocity import VelocityCalculator
from src.analytics.calculators.sprint_report import SprintReportCalculator
from src.analytics.calculators.cfd import calculate_cfd
from src.analytics.calculators.cycle_time import calculate_cycle_time
from src.analytics.calculators.work_distribution import calculate_work_distribution
from src.analytics.calculators.issue_trend import calculate_issue_trend
from src.analytics.adapters.base import BaseAnalyticsAdapter


class AnalyticsService:
    """
    Main analytics service for generating charts and reports.
    
    This service can use either mock data or real data from PM providers.
    """
    
    def __init__(self, data_source: str = "mock", adapter: Optional[BaseAnalyticsAdapter] = None):
        """
        Initialize analytics service.
        
        Args:
            data_source: Data source to use ("mock" or "real")
            adapter: Optional analytics adapter for fetching real data
        """
        self.data_source = data_source
        self.mock_generator = MockDataGenerator()
        self.adapter = adapter
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
        
        if data_source == "real" and not adapter:
            raise ValueError("Analytics adapter is required when data_source is 'real'")
    
    async def get_burndown_chart(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        scope_type: Literal["story_points", "tasks", "hours"] = "story_points"
    ) -> ChartResponse:
        """
        Get burndown chart for a sprint.
        
        Args:
            project_id: Project identifier
            sprint_id: Sprint identifier (if None, gets current sprint)
            scope_type: What to measure (story_points, tasks, or hours)
        
        Returns:
            ChartResponse with burndown data
        """
        cache_key = f"burndown_{project_id}_{sprint_id}_{scope_type}"
        
        # Check cache
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Get sprint data
        if self.data_source == "mock":
            sprint_data = self.mock_generator.generate_sprint_data(
                sprint_id=sprint_id or "SPRINT-1",
                project_id=project_id
            )
        else:
            # Fetch real data from adapter
            sprint_data = await self.adapter.get_burndown_data(project_id, sprint_id, scope_type)
            # If adapter returns None (e.g., no sprints found), fallback to mock data
            if sprint_data is None:
                logger.warning(f"Adapter returned no data for project {project_id}, falling back to mock data")
                sprint_data = self.mock_generator.generate_sprint_data(
                    sprint_id=sprint_id or "SPRINT-1",
                    project_id=project_id
                )
        
        # Calculate burndown
        result = BurndownCalculator.calculate(sprint_data, scope_type)
        
        # Cache result
        self._set_cache(cache_key, result)
        
        return result
    
    async def get_velocity_chart(
        self,
        project_id: str,
        sprint_count: int = 6
    ) -> ChartResponse:
        """
        Get velocity chart for recent sprints.
        
        Args:
            project_id: Project identifier
            sprint_count: Number of recent sprints to include
        
        Returns:
            ChartResponse with velocity data
        """
        cache_key = f"velocity_{project_id}_{sprint_count}"
        
        # Check cache
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Get sprint history
        if self.data_source == "mock":
            sprint_history = self.mock_generator.generate_sprint_history(
                project_id=project_id,
                num_sprints=sprint_count
            )
        else:
            # Fetch real data from adapter
            sprint_history = await self.adapter.get_velocity_data(project_id, sprint_count)
            # If adapter returns None or empty, fallback to mock data
            if not sprint_history:
                logger.warning(f"Adapter returned no velocity data for project {project_id}, falling back to mock data")
                sprint_history = self.mock_generator.generate_sprint_history(
                    project_id=project_id,
                    num_sprints=sprint_count
                )
        
        # Calculate velocity
        result = VelocityCalculator.calculate(sprint_history)
        
        # Cache result
        self._set_cache(cache_key, result)
        
        return result
    
    async def get_sprint_report(
        self,
        sprint_id: str,
        project_id: str
    ) -> SprintReport:
        """
        Get comprehensive sprint report.
        
        Args:
            sprint_id: Sprint identifier
            project_id: Project identifier
        
        Returns:
            SprintReport with summary and metrics
        """
        cache_key = f"sprint_report_{sprint_id}"
        
        # Check cache
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Get sprint data
        if self.data_source == "mock":
            sprint_data = self.mock_generator.generate_sprint_data(
                sprint_id=sprint_id,
                project_id=project_id
            )
        else:
            # Fetch real data from adapter
            sprint_data = await self.adapter.get_sprint_report_data(sprint_id, project_id)
            # If adapter returns None, fallback to mock data
            if sprint_data is None:
                logger.warning(f"Adapter returned no sprint report data for sprint {sprint_id}, falling back to mock data")
                sprint_data = self.mock_generator.generate_sprint_data(
                    sprint_id=sprint_id,
                    project_id=project_id
                )
        
        # Generate report
        result = SprintReportCalculator.calculate(sprint_data)
        
        # Cache result
        self._set_cache(cache_key, result)
        
        return result
    
    def get_project_summary(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Get high-level project summary with key metrics.
        
        Args:
            project_id: Project identifier
        
        Returns:
            Dictionary with project summary
        """
        cache_key = f"project_summary_{project_id}"
        
        # Check cache
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Get recent sprints for summary
        sprint_history = self.mock_generator.generate_sprint_history(
            project_id=project_id,
            num_sprints=3
        )
        
        if not sprint_history:
            return {
                "project_id": project_id,
                "error": "No sprint data available"
            }
        
        # Calculate summary metrics
        latest_sprint = sprint_history[-1]
        velocity_chart = VelocityCalculator.calculate(sprint_history)
        
        total_items = sum(len(sprint.work_items) for sprint in sprint_history)
        completed_items = sum(
            len([item for item in sprint.work_items if item.status.value == "done"])
            for sprint in sprint_history
        )
        
        summary = {
            "project_id": project_id,
            "current_sprint": {
                "id": latest_sprint.id,
                "name": latest_sprint.name,
                "status": latest_sprint.status,
                "progress": round((latest_sprint.completed_points or 0) / (latest_sprint.planned_points or 1) * 100, 1)
            },
            "velocity": {
                "average": velocity_chart.metadata.get("average_velocity", 0),
                "latest": velocity_chart.metadata.get("latest_velocity", 0),
                "trend": velocity_chart.metadata.get("trend", "stable")
            },
            "overall_stats": {
                "total_items": total_items,
                "completed_items": completed_items,
                "completion_rate": round(completed_items / total_items * 100, 1) if total_items > 0 else 0
            },
            "team_size": len(latest_sprint.team_members),
            "generated_at": datetime.now().isoformat()
        }
        
        # Cache result
        self._set_cache(cache_key, summary)
        
        return summary
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired"""
        if key in self._cache:
            cached_item = self._cache[key]
            if datetime.now() - cached_item["timestamp"] < timedelta(seconds=self._cache_ttl):
                return cached_item["data"]
            else:
                # Expired, remove from cache
                del self._cache[key]
        return None
    
    def _set_cache(self, key: str, data: Any):
        """Set item in cache with timestamp"""
        self._cache[key] = {
            "data": data,
            "timestamp": datetime.now()
        }
    
    async def get_cfd_chart(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        days_back: int = 30
    ) -> ChartResponse:
        """
        Get Cumulative Flow Diagram for a project or sprint.
        
        Args:
            project_id: Project identifier
            sprint_id: Sprint identifier (if None, uses date range)
            days_back: Number of days to look back (default: 30)
        
        Returns:
            ChartResponse with CFD data
        """
        cache_key = f"cfd_{project_id}_{sprint_id}_{days_back}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Get data based on source
        if self.data_source == "mock":
            # Generate mock CFD data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Generate work items with status history
            work_items = self.mock_generator.generate_cfd_data(
                num_items=50,
                start_date=start_date,
                end_date=end_date
            )
            
            # Calculate CFD
            chart = calculate_cfd(
                work_items=work_items,
                start_date=start_date,
                end_date=end_date,
                statuses=["To Do", "In Progress", "In Review", "Done"]
            )
        else:
            # Fetch real data from adapter
            cfd_data = await self.adapter.get_cfd_data(project_id, sprint_id, days_back)
            chart = calculate_cfd(
                work_items=cfd_data["work_items"],
                start_date=cfd_data["start_date"],
                end_date=cfd_data["end_date"],
                statuses=cfd_data["statuses"]
            )
        
        # Cache result
        self._set_cache(cache_key, chart)
        
        return chart
    
    async def get_cycle_time_chart(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        days_back: int = 60
    ) -> ChartResponse:
        """
        Get Cycle Time / Control Chart for a project or sprint.
        
        Args:
            project_id: Project identifier
            sprint_id: Sprint identifier (if None, uses date range)
            days_back: Number of days to look back (default: 60)
        
        Returns:
            ChartResponse with cycle time data
        """
        cache_key = f"cycle_time_{project_id}_{sprint_id}_{days_back}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Get data based on source
        if self.data_source == "mock":
            # Generate mock cycle time data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Generate work items with cycle time
            work_items = self.mock_generator.generate_cycle_time_data(
                num_items=50,
                start_date=start_date,
                end_date=end_date
            )
            
            # Calculate cycle time metrics
            chart = calculate_cycle_time(work_items=work_items)
        else:
            # Fetch real data from adapter
            work_items = await self.adapter.get_cycle_time_data(project_id, sprint_id, days_back)
            chart = calculate_cycle_time(work_items=work_items)
        
        # Cache result
        self._set_cache(cache_key, chart)
        
        return chart
    
    async def get_work_distribution_chart(
        self,
        project_id: str,
        dimension: str = "assignee",
        sprint_id: Optional[str] = None
    ) -> ChartResponse:
        """
        Get Work Distribution chart for a project.
        
        Args:
            project_id: Project identifier
            dimension: One of 'assignee', 'priority', 'type', 'status'
            sprint_id: Sprint identifier (optional filter)
        
        Returns:
            ChartResponse with work distribution data
        """
        cache_key = f"work_distribution_{project_id}_{dimension}_{sprint_id}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Get data based on source
        if self.data_source == "mock":
            # Generate mock work distribution data
            work_items = self.mock_generator.generate_work_distribution_data(num_items=50)
            
            # Calculate distribution
            chart = calculate_work_distribution(
                work_items=work_items,
                dimension=dimension
            )
        else:
            # Fetch real data from adapter
            work_items = await self.adapter.get_work_distribution_data(project_id, sprint_id)
            chart = calculate_work_distribution(
                work_items=work_items,
                dimension=dimension
            )
        
        # Cache result
        self._set_cache(cache_key, chart)
        
        return chart
    
    async def get_issue_trend_chart(
        self,
        project_id: str,
        days_back: int = 30,
        sprint_id: Optional[str] = None
    ) -> ChartResponse:
        """
        Get Issue Trend Analysis chart for a project.
        
        Args:
            project_id: Project identifier
            days_back: Number of days to look back (default: 30)
            sprint_id: Sprint identifier (optional filter)
        
        Returns:
            ChartResponse with issue trend data
        """
        cache_key = f"issue_trend_{project_id}_{days_back}_{sprint_id}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Get data based on source
        if self.data_source == "mock":
            # Generate mock issue trend data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            work_items = self.mock_generator.generate_issue_trend_data(
                num_items=100,
                start_date=start_date,
                end_date=end_date
            )
            
            # Calculate trend
            chart = calculate_issue_trend(
                work_items=work_items,
                start_date=start_date,
                end_date=end_date
            )
        else:
            # Fetch real data from adapter
            trend_data = await self.adapter.get_issue_trend_data(project_id, days_back, sprint_id)
            chart = calculate_issue_trend(
                work_items=trend_data["work_items"],
                start_date=trend_data["start_date"],
                end_date=trend_data["end_date"]
            )
        
        # Cache result
        self._set_cache(cache_key, chart)
        
        return chart
    
    def clear_cache(self):
        """Clear all cached data"""
        self._cache.clear()

