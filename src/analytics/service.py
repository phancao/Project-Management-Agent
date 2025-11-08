"""
Analytics service - main entry point for chart generation.

Orchestrates data fetching, calculation, and caching for all chart types.
"""

from typing import Optional, Literal, Dict, Any
from datetime import datetime, timedelta

from src.analytics.models import ChartResponse, SprintReport
from src.analytics.mock_data import MockDataGenerator
from src.analytics.calculators.burndown import BurndownCalculator
from src.analytics.calculators.velocity import VelocityCalculator
from src.analytics.calculators.sprint_report import SprintReportCalculator
from src.analytics.calculators.cfd import calculate_cfd


class AnalyticsService:
    """
    Main analytics service for generating charts and reports.
    
    This service uses mock data by default, but is designed to be easily
    extended with real data adapters for JIRA, OpenProject, etc.
    """
    
    def __init__(self, data_source: str = "mock"):
        """
        Initialize analytics service.
        
        Args:
            data_source: Data source to use ("mock", "jira", "openproject")
        """
        self.data_source = data_source
        self.mock_generator = MockDataGenerator()
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
    
    def get_burndown_chart(
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
            # TODO: Implement real data adapters
            raise NotImplementedError(f"Data source '{self.data_source}' not yet implemented")
        
        # Calculate burndown
        result = BurndownCalculator.calculate(sprint_data, scope_type)
        
        # Cache result
        self._set_cache(cache_key, result)
        
        return result
    
    def get_velocity_chart(
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
            # TODO: Implement real data adapters
            raise NotImplementedError(f"Data source '{self.data_source}' not yet implemented")
        
        # Calculate velocity
        result = VelocityCalculator.calculate(sprint_history)
        
        # Cache result
        self._set_cache(cache_key, result)
        
        return result
    
    def get_sprint_report(
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
            # TODO: Implement real data adapters
            raise NotImplementedError(f"Data source '{self.data_source}' not yet implemented")
        
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
    
    def get_cfd_chart(
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
            # TODO: Implement real data adapters
            raise NotImplementedError(f"Data source '{self.data_source}' not yet implemented for CFD")
        
        # Cache result
        self._set_cache(cache_key, chart)
        
        return chart
    
    def clear_cache(self):
        """Clear all cached data"""
        self._cache.clear()

