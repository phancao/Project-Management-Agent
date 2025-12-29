"""
Burndown chart calculator.

Generates burndown chart data showing ideal vs actual remaining work over time.
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Literal

from backend.analytics.models import (
    ChartResponse, ChartSeries, ChartDataPoint, ChartType,
    SprintData, WorkItem, TaskStatus
)

logger = logging.getLogger(__name__)


class BurndownCalculator:
    """Calculates burndown chart data"""
    
    @staticmethod
    def calculate(
        sprint_data: SprintData,
        scope_type: Literal["story_points", "tasks", "hours"] = "story_points"
    ) -> ChartResponse:
        """
        Calculate burndown chart for a sprint.
        
        Args:
            sprint_data: Sprint data with work items
            scope_type: What to measure - story points, task count, or hours
        
        Returns:
            ChartResponse with ideal and actual burndown series
        """
        
        # Get total scope based on type
        if scope_type == "story_points":
            total_scope = sum(item.story_points or 0 for item in sprint_data.work_items)
        elif scope_type == "hours":
            total_scope = sum(item.estimated_hours or 0 for item in sprint_data.work_items)
        else:  # tasks
            total_scope = len(sprint_data.work_items)
        
        # Account for scope changes
        if scope_type == "story_points":
            added_scope = sum(item.story_points or 0 for item in sprint_data.added_items)
            removed_scope = sum(item.story_points or 0 for item in sprint_data.removed_items)
        elif scope_type == "hours":
            added_scope = sum(item.estimated_hours or 0 for item in sprint_data.added_items)
            removed_scope = sum(item.estimated_hours or 0 for item in sprint_data.removed_items)
        else:
            added_scope = len(sprint_data.added_items)
            removed_scope = len(sprint_data.removed_items)
        
        final_scope = total_scope + added_scope - removed_scope
        
        # Generate ideal line (linear burndown)
        ideal_series = BurndownCalculator._calculate_ideal_line(
            sprint_data.start_date,
            sprint_data.end_date,
            final_scope
        )
        
        # Generate actual line (based on completed work)
        actual_series = BurndownCalculator._calculate_actual_line(
            sprint_data,
            scope_type,
            final_scope
        )
        
        # Calculate metadata
        completed = final_scope - actual_series.data[-1].value if actual_series.data else 0
        remaining = actual_series.data[-1].value if actual_series.data else final_scope
        completion_percentage = (completed / final_scope * 100) if final_scope > 0 else 0
        
        # Determine if on track (actual <= ideal at current point)
        on_track = True
        if len(actual_series.data) > 0 and len(ideal_series.data) > 0:
            current_actual = actual_series.data[-1].value
            # Find corresponding ideal value
            current_date = actual_series.data[-1].date
            ideal_value = next(
                (point.value for point in ideal_series.data if point.date.date() == current_date.date()),
                ideal_series.data[-1].value
            )
            on_track = current_actual <= ideal_value
        
        return ChartResponse(
            chart_type=ChartType.BURNDOWN,
            title=f"{sprint_data.name} Burndown Chart",
            series=[ideal_series, actual_series],
            metadata={
                "total_scope": round(final_scope, 2),
                "remaining": round(remaining, 2),
                "completed": round(completed, 2),
                "completion_percentage": round(completion_percentage, 2),
                "on_track": on_track,
                "scope_type": scope_type,
                "scope_changes": {
                    "added": round(added_scope, 2),
                    "removed": round(removed_scope, 2),
                    "net": round(added_scope - removed_scope, 2)
                },
                "sprint_days": (sprint_data.end_date - sprint_data.start_date).days,
                "status": sprint_data.status
            }
        )
    
    @staticmethod
    def _calculate_ideal_line(
        start_date: date,
        end_date: date,
        total_scope: float
    ) -> ChartSeries:
        """Calculate ideal linear burndown"""
        data_points = []
        
        total_days = (end_date - start_date).days
        if total_days == 0:
            total_days = 1
        
        daily_burndown = total_scope / total_days
        
        current_date = start_date
        remaining = total_scope
        
        while current_date <= end_date:
            data_points.append(ChartDataPoint(
                date=datetime.combine(current_date, datetime.min.time()),
                value=round(max(0, remaining), 2),
                label=current_date.strftime("%Y-%m-%d")
            ))
            
            remaining -= daily_burndown
            current_date += timedelta(days=1)
        
        return ChartSeries(
            name="Ideal",
            data=data_points,
            color="#94a3b8",  # Gray
            type="line"
        )
    
    @staticmethod
    def _calculate_actual_line(
        sprint_data: SprintData,
        scope_type: Literal["story_points", "tasks", "hours"],
        total_scope: float
    ) -> ChartSeries:
        """Calculate actual burndown based on completed work"""
        # Ensure logger is available (defensive check)
        from logging import getLogger
        _logger = getLogger(__name__)
        
        data_points = []
        
        # Get initial scope at sprint start
        if scope_type == "story_points":
            initial_scope = sum(item.story_points or 0 for item in sprint_data.work_items)
        elif scope_type == "hours":
            initial_scope = sum(item.estimated_hours or 0 for item in sprint_data.work_items)
        else:
            initial_scope = len(sprint_data.work_items)
        
        current_date = sprint_data.start_date
        end_date = min(sprint_data.end_date, date.today())
        
        while current_date <= end_date:
            # Calculate remaining work at this date
            completed_work = 0
            
            for item in sprint_data.work_items:
                # Log each item for debugging
                    f"[BurndownCalculator] Checking item {item.id}: "
                    f"status={item.status}, "
                    f"completed_at={item.completed_at}, "
                    f"story_points={item.story_points}"
                )
                
                if item.status == TaskStatus.DONE:
                    # If task is DONE, count it toward burndown
                    # Use completed_at if available, otherwise use sprint end date or current date
                    completion_date = item.completed_at
                    if not completion_date:
                        # If no completion date but task is done, use sprint end date
                        # This handles cases where tasks are marked done but don't have completion dates
                        completion_date = datetime.combine(sprint_data.end_date, datetime.min.time())
                            f"[BurndownCalculator] Item {item.id} is DONE but no completion_date, "
                            f"using sprint end date: {completion_date.date()}"
                        )
                    
                    if completion_date.date() <= current_date:
                        work_value = 0
                        if scope_type == "story_points":
                            work_value = item.story_points or 0
                        elif scope_type == "hours":
                            work_value = item.estimated_hours or 0
                        else:
                            work_value = 1
                        
                        completed_work += work_value
                            f"[BurndownCalculator] Item {item.id} counted as completed: "
                            f"{work_value} {scope_type} on {current_date}"
                        )
            
            # Account for scope changes up to current date
            added_work = 0
            removed_work = 0
            
            for item in sprint_data.added_items:
                if item.created_at.date() <= current_date:
                    if scope_type == "story_points":
                        added_work += item.story_points or 0
                    elif scope_type == "hours":
                        added_work += item.estimated_hours or 0
                    else:
                        added_work += 1
            
            for item in sprint_data.removed_items:
                if item.created_at.date() <= current_date:
                    if scope_type == "story_points":
                        removed_work += item.story_points or 0
                    elif scope_type == "hours":
                        removed_work += item.estimated_hours or 0
                    else:
                        removed_work += 1
            
            current_scope = initial_scope + added_work - removed_work
            remaining = current_scope - completed_work
            
            data_points.append(ChartDataPoint(
                date=datetime.combine(current_date, datetime.min.time()),
                value=round(max(0, remaining), 2),
                label=current_date.strftime("%Y-%m-%d"),
                metadata={
                    "completed": round(completed_work, 2),
                    "scope": round(current_scope, 2)
                }
            ))
            
            current_date += timedelta(days=1)
        
        return ChartSeries(
            name="Actual",
            data=data_points,
            color="#3b82f6",  # Blue
            type="line"
        )







