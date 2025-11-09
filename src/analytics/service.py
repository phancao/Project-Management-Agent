"""Analytics service - main entry point for chart generation."""

from typing import Optional, Literal, Dict, Any, List, Union
from datetime import datetime, timedelta, date
import logging

from src.analytics.models import (
    ChartResponse,
    SprintReport,
    SprintData,
    WorkItem,
    WorkItemType,
    TaskStatus,
    Priority,
)
from src.pm_providers.models import PMTask

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
            adapter: Optional analytics adapter for fetching real data (None = empty data)
        """
        self.data_source = data_source
        self.mock_generator = MockDataGenerator()
        self.adapter = adapter
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Note: adapter can be None when data_source is "real" - this means return empty data
    
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
            # Check if adapter is available
            if not self.adapter:
                logger.info(f"No adapter available for project {project_id}, returning empty chart")
                return ChartResponse(
                    chart_type="burndown",
                    title="Sprint Burndown",
                    data=[],
                    metadata={"message": "No data source configured for this project."}
                )
            
            # Fetch real data from adapter
            sprint_data = await self.adapter.get_burndown_data(project_id, sprint_id, scope_type)
            # If adapter returns None (e.g., no sprints found), return empty chart
            if sprint_data is None:
                logger.info(f"No sprint data found for project {project_id}, returning empty chart")
                return ChartResponse(
                    chart_type="burndown",
                    title="Sprint Burndown",
                    data=[],
                    metadata={"message": "No sprint data available. Please configure sprints in your project."}
                )
        
        if not isinstance(sprint_data, SprintData):
            sprint_data = self._payload_to_sprint_data(sprint_data, project_id)

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
            if not sprint_history:
                logger.info(f"No sprint history found for project {project_id}, returning empty chart")
                return ChartResponse(
                    chart_type="velocity",
                    title="Team Velocity",
                    data=[],
                    metadata={"message": "No sprint history available. Please configure sprints in your project."}
                )
            sprint_history = [
                self._payload_to_sprint_data(payload, project_id)
                if not isinstance(payload, SprintData)
                else payload
                for payload in sprint_history
            ]
        
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
            sprint_data_dict = await self.adapter.get_sprint_report_data(sprint_id, project_id)
            # If adapter returns None, return empty report
            if sprint_data_dict is None:
                logger.info(f"No sprint data found for sprint {sprint_id}, returning empty report")
                from datetime import date
                return SprintReport(
                    sprint_id=sprint_id,
                    sprint_name="Unknown Sprint",
                    start_date=date.today(),
                    end_date=date.today(),
                    status="unknown",
                    duration_days=0,
                    planned_points=0,
                    completed_points=0,
                    completion_percentage=0,
                    planned_tasks=0,
                    completed_tasks=0,
                    incomplete_tasks=0,
                    added_tasks=0,
                    removed_tasks=0,
                    team_members=[],
                    tasks_by_status={},
                    tasks_by_assignee={},
                    message="Sprint not found or no data available."
                )
            else:
                if isinstance(sprint_data_dict, SprintData):
                    sprint_data = sprint_data_dict
                else:
                    sprint_data = self._payload_to_sprint_data(
                        sprint_data_dict,
                        project_id,
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

    @staticmethod
    def _parse_datetime(value: Optional[Union[str, datetime, date]]) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            if value.endswith("Z"):
                fixed = value.replace("Z", "+00:00")
                try:
                    return datetime.fromisoformat(fixed)
                except ValueError:
                    return None
            return None

    @staticmethod
    def _map_status(value: Optional[Union[str, TaskStatus]]) -> TaskStatus:
        if isinstance(value, TaskStatus):
            return value
        text = (value or "").lower()
        if "review" in text:
            return TaskStatus.IN_REVIEW
        if "progress" in text:
            return TaskStatus.IN_PROGRESS
        if any(word in text for word in ("done", "closed", "completed", "resolved")):
            return TaskStatus.DONE
        if "block" in text:
            return TaskStatus.BLOCKED
        return TaskStatus.TODO

    @staticmethod
    def _map_type(value: Optional[Union[str, WorkItemType]]) -> WorkItemType:
        if isinstance(value, WorkItemType):
            return value
        text = (value or "").lower()
        if "story" in text:
            return WorkItemType.STORY
        if "bug" in text:
            return WorkItemType.BUG
        if "epic" in text:
            return WorkItemType.EPIC
        if "sub" in text:
            return WorkItemType.SUBTASK
        return WorkItemType.TASK

    @staticmethod
    def _map_priority(value: Optional[Union[str, Priority]]) -> Priority:
        if isinstance(value, Priority):
            return value
        text = (value or "").lower()
        if text in {"critical", "highest"}:
            return Priority.CRITICAL
        if text == "high":
            return Priority.HIGH
        if text in {"low", "lowest"}:
            return Priority.LOW
        return Priority.MEDIUM

    @staticmethod
    def _map_sprint_status(value: Optional[str]) -> str:
        text = (value or "").lower()
        if "plan" in text:
            return "planning"
        if any(word in text for word in ("done", "closed", "completed")):
            return "completed"
        if "cancel" in text:
            return "cancelled"
        return "active"

    @classmethod
    def _to_work_item(cls, data: Union[Dict[str, Any], WorkItem, PMTask]) -> WorkItem:
        if isinstance(data, WorkItem):
            return data

        if isinstance(data, PMTask):
            raw = data.raw_data or {}
            story_points = raw.get("storyPoints")
            if story_points is None and data.estimated_hours:
                story_points = data.estimated_hours / 8
            created = cls._parse_datetime(data.created_at) or datetime.utcnow()
            completed = cls._parse_datetime(data.completed_at)
            return WorkItem(
                id=str(data.id or "unknown"),
                title=str(data.title or "Untitled"),
                type=cls._map_type(raw.get("type")),
                status=cls._map_status(data.status),
                priority=cls._map_priority(data.priority),
                story_points=story_points,
                estimated_hours=data.estimated_hours,
                actual_hours=data.actual_hours,
                assigned_to=data.assignee_id,
                created_at=created,
                completed_at=completed,
            )

        created = cls._parse_datetime(data.get("created_at"))
        if not created:
            created = datetime.utcnow()
        completed = cls._parse_datetime(data.get("completed_at"))
        return WorkItem(
            id=str(data.get("id") or "unknown"),
            title=str(data.get("title") or "Untitled"),
            type=cls._map_type(data.get("type")),
            status=cls._map_status(data.get("status")),
            priority=cls._map_priority(data.get("priority")),
            story_points=data.get("story_points"),
            estimated_hours=data.get("estimated_hours"),
            actual_hours=data.get("actual_hours"),
            assigned_to=data.get("assigned_to"),
            created_at=created,
            completed_at=completed,
        )

    @classmethod
    def _payload_to_sprint_data(
        cls,
        payload: Dict[str, Any],
        project_id: str,
    ) -> SprintData:
        sprint_info = payload.get("sprint", {}) or {}
        project = str(payload.get("project_id") or project_id)

        start_dt = cls._parse_datetime(sprint_info.get("start_date"))
        end_dt = cls._parse_datetime(sprint_info.get("end_date"))
        start_date = start_dt.date() if start_dt else date.today()
        end_date = end_dt.date() if end_dt else start_date

        work_items = [
            cls._to_work_item(item)
            for item in payload.get("tasks", [])
        ]
        added_items = [
            cls._to_work_item(item)
            for item in payload.get("added_items", [])
        ]
        removed_items = [
            cls._to_work_item(item)
            for item in payload.get("removed_items", [])
        ]

        planned = payload.get("planned_points")
        if planned is None:
            planned = sum(item.story_points or 0 for item in work_items)

        completed = payload.get("completed_points")
        if completed is None:
            completed = sum(
                item.story_points or 0
                for item in work_items
                if item.status == TaskStatus.DONE and item.completed_at
            )

        return SprintData(
            id=str(sprint_info.get("id") or "unknown"),
            name=str(sprint_info.get("name") or "Sprint"),
            project_id=project,
            start_date=start_date,
            end_date=end_date,
            status=cls._map_sprint_status(sprint_info.get("status")),
            planned_points=planned,
            completed_points=completed,
            work_items=work_items,
            added_items=added_items,
            removed_items=removed_items,
            team_members=payload.get("team_members", []),
        )

