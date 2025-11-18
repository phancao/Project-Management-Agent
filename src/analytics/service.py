"""Analytics service - main entry point for chart generation."""

from typing import Optional, Literal, Dict, Any, List, Union
from datetime import datetime, timedelta, date
import logging

from src.analytics.models import (
    ChartResponse,
    ChartType,
    SprintReport,
    SprintData,
    WorkItem,
    WorkItemType,
    TaskStatus,
    Priority,
)
from src.pm_providers.models import PMTask

logger = logging.getLogger(__name__)
from src.analytics.calculators.burndown import BurndownCalculator
from src.analytics.calculators.velocity import VelocityCalculator
from src.analytics.calculators.sprint_report import SprintReportCalculator
from src.analytics.calculators.cfd import calculate_cfd
from src.analytics.calculators.cycle_time import calculate_cycle_time
from src.analytics.calculators.work_distribution import calculate_work_distribution
from src.analytics.calculators.issue_trend import calculate_issue_trend
from src.analytics.adapters.base import BaseAnalyticsAdapter


class AnalyticsService:
    """Main analytics service for generating charts and reports."""

    def __init__(self, adapter: Optional[BaseAnalyticsAdapter] = None):
        """
        Initialize analytics service.

        Args:
            adapter: Analytics adapter for fetching data from the configured PM provider.
        """
        self.adapter = adapter
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
    
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
        
        if not self.adapter:
            logger.info("No analytics adapter configured for project %s", project_id)
            return ChartResponse(
                chart_type=ChartType.BURNDOWN,
                title="Sprint Burndown",
                series=[],
                metadata={"message": "No data source configured for this project."},
            )

        sprint_data = await self.adapter.get_burndown_data(project_id, sprint_id, scope_type)
        if sprint_data is None:
            logger.info("No sprint data found for project %s", project_id)
            return ChartResponse(
                chart_type=ChartType.BURNDOWN,
                title="Sprint Burndown",
                series=[],
                metadata={
                    "message": "No sprint data available. Please configure sprints in your project."
                },
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
        
        if not self.adapter:
            logger.info("No analytics adapter configured for project %s", project_id)
            return ChartResponse(
                chart_type=ChartType.VELOCITY,
                title="Team Velocity",
                series=[],
                metadata={"message": "No data source configured for this project."},
            )

        sprint_history = await self.adapter.get_velocity_data(project_id, sprint_count)
        if not sprint_history:
            logger.info("No sprint history found for project %s", project_id)
            return ChartResponse(
                chart_type=ChartType.VELOCITY,
                title="Team Velocity",
                series=[],
                metadata={
                    "message": "No sprint history available. Please configure sprints in your project."
                },
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
        
        if not self.adapter:
            raise ValueError("Analytics adapter not configured for this project.")

        sprint_data_payload = await self.adapter.get_sprint_report_data(sprint_id, project_id)
        if sprint_data_payload is None:
            raise ValueError(f"Sprint {sprint_id} not found or no data available.")

        if isinstance(sprint_data_payload, SprintData):
            sprint_data = sprint_data_payload
        else:
            sprint_data = self._payload_to_sprint_data(sprint_data_payload, project_id)
        
        # Generate report
        result = SprintReportCalculator.calculate(sprint_data)
        
        # Cache result
        self._set_cache(cache_key, result)
        
        return result
    
    async def get_project_summary(self, project_id: str) -> Dict[str, Any]:
        """
        Get high-level project summary with key metrics sourced from the provider.

        Args:
            project_id: Project identifier

        Returns:
            Dictionary with project summary
        """
        cache_key = f"project_summary_{project_id}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        if not self.adapter:
            raise ValueError("Analytics adapter not configured for this project.")

        velocity_payloads = await self.adapter.get_velocity_data(project_id, sprint_count=3)
        if not velocity_payloads:
            summary = {
                "project_id": project_id,
                "error": "No sprint data available",
            }
            self._set_cache(cache_key, summary)
            return summary

        sprints: List[SprintData] = [
            self._payload_to_sprint_data(payload, project_id)
            if not isinstance(payload, SprintData)
            else payload
            for payload in velocity_payloads
        ]
        velocity_chart = VelocityCalculator.calculate(sprints)

        latest_payload = velocity_payloads[-1]
        latest_sprint_id = None
        if isinstance(latest_payload, dict):
            latest_sprint_id = latest_payload.get("sprint_id") or latest_payload.get("id")
        elif isinstance(latest_payload, SprintData):
            latest_sprint_id = latest_payload.id

        latest_report: Optional[SprintData] = None
        if latest_sprint_id:
            try:
                sprint_report_payload = await self.adapter.get_sprint_report_data(
                    latest_sprint_id, project_id
                )
                if isinstance(sprint_report_payload, SprintData):
                    latest_report = sprint_report_payload
                elif sprint_report_payload:
                    latest_report = self._payload_to_sprint_data(sprint_report_payload, project_id)
            except Exception as exc:  # pragma: no cover - best effort logging
                logger.warning(
                    "Failed to fetch detailed sprint report for %s: %s",
                    latest_sprint_id,
                    exc,
                )

        if latest_report is None and sprints:
            latest_report = sprints[-1]

        total_items = sum(len(sprint.work_items) for sprint in sprints)
        completed_items = sum(
            len([item for item in sprint.work_items if item.status == TaskStatus.DONE])
            for sprint in sprints
        )

        team_size = len(latest_report.team_members) if latest_report else 0
        progress = 0.0
        if latest_report and latest_report.planned_points:
            progress = (
                (latest_report.completed_points or 0) / latest_report.planned_points * 100
            )

        summary = {
            "project_id": project_id,
            "current_sprint": {
                "id": latest_report.id if latest_report else latest_sprint_id,
                "name": latest_report.name if latest_report else latest_sprint_id,
                "status": latest_report.status if latest_report else "unknown",
                "progress": round(progress, 1) if progress else 0,
            },
            "velocity": {
                "average": velocity_chart.metadata.get("average_velocity", 0),
                "latest": velocity_chart.metadata.get("latest_velocity", 0),
                "trend": velocity_chart.metadata.get("trend", "stable"),
            },
            "overall_stats": {
                "total_items": total_items,
                "completed_items": completed_items,
                "completion_rate": round(completed_items / total_items * 100, 1)
                if total_items > 0
                else 0,
            },
            "team_size": team_size,
            "recent_trends": velocity_chart.metadata.get("velocity_by_sprint", []),
        }

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
        
        if not self.adapter:
            logger.info("No analytics adapter configured for project %s", project_id)
            return ChartResponse(
                chart_type=ChartType.CFD,
                title="Cumulative Flow Diagram",
                series=[],
                metadata={"message": "No data source configured for this project."},
            )

        cfd_data = await self.adapter.get_cfd_data(project_id, sprint_id, days_back)
        chart = calculate_cfd(
            work_items=cfd_data["work_items"],
            start_date=cfd_data["start_date"],
            end_date=cfd_data["end_date"],
            statuses=cfd_data["statuses"],
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
        
        if not self.adapter:
            logger.info("No analytics adapter configured for project %s", project_id)
            return ChartResponse(
                chart_type=ChartType.CYCLE_TIME,
                title="Cycle Time",
                series=[],
                metadata={"message": "No data source configured for this project."},
            )

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
        
        if not self.adapter:
            logger.info("No analytics adapter configured for project %s", project_id)
            return ChartResponse(
                chart_type=ChartType.DISTRIBUTION,
                title="Work Distribution",
                series=[],
                metadata={"message": "No data source configured for this project."},
            )

        work_items = await self.adapter.get_work_distribution_data(project_id, sprint_id)
        chart = calculate_work_distribution(work_items=work_items, dimension=dimension)
        
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
        
        if not self.adapter:
            logger.info("No analytics adapter configured for project %s", project_id)
            return ChartResponse(
                chart_type=ChartType.TREND,
                title="Issue Trend",
                series=[],
                metadata={"message": "No data source configured for this project."},
            )

        trend_data = await self.adapter.get_issue_trend_data(project_id, days_back, sprint_id)
        chart = calculate_issue_trend(
            work_items=trend_data["work_items"],
            start_date=trend_data["start_date"],
            end_date=trend_data["end_date"],
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
            
            # Determine status: if task is completed (100% or marked done), use DONE
            # Otherwise map from status string
            status = cls._map_status(data.status)
            # Check if task is actually completed (100% or marked as done)
            if data.raw_data:
                # Check percentage complete for OpenProject
                percentage_complete = raw.get("percentageComplete") or raw.get("percentage_complete")
                if percentage_complete is not None:
                    try:
                        if float(percentage_complete) >= 100.0:
                            status = TaskStatus.DONE
                    except (ValueError, TypeError):
                        pass
                # Check status.is_closed for OpenProject
                status_obj = raw.get("_embedded", {}).get("status", {}) or raw.get("status", {})
                if isinstance(status_obj, dict):
                    is_closed = status_obj.get("isClosed", False)
                    if is_closed:
                        status = TaskStatus.DONE
            
            return WorkItem(
                id=str(data.id or "unknown"),
                title=str(data.title or "Untitled"),
                type=cls._map_type(raw.get("type")),
                status=status,
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
        
        # Determine status: if task is marked as completed, use DONE
        # Otherwise map from status string
        status = cls._map_status(data.get("status"))
        # Check if task is marked as completed in the data (this is the key check!)
        if data.get("completed") is True:
            status = TaskStatus.DONE
            # Log this important status change
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"[AnalyticsService] Task {data.get('id')} marked as completed=True, "
                f"setting status to DONE (was: {status})"
            )
        # Also check percentage complete
        percentage_complete = data.get("percentage_complete") or data.get("percentageComplete")
        if percentage_complete is not None:
            try:
                if float(percentage_complete) >= 100.0:
                    status = TaskStatus.DONE
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(
                        f"[AnalyticsService] Task {data.get('id')} has 100% completion, "
                        f"setting status to DONE"
                    )
            except (ValueError, TypeError):
                pass
        
        return WorkItem(
            id=str(data.get("id") or "unknown"),
            title=str(data.get("title") or "Untitled"),
            type=cls._map_type(data.get("type")),
            status=status,
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
        if not sprint_info:
            sprint_info = {
                "id": payload.get("sprint_id") or payload.get("id"),
                "name": payload.get("name"),
                "project_id": payload.get("project_id"),
                "start_date": payload.get("start_date"),
                "end_date": payload.get("end_date"),
                "status": payload.get("status"),
            }
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

