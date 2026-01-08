"""
Capacity Planning Calculator

Calculates resource demand vs. capacity over time.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
from collections import defaultdict
import math

from ..models import (
    WorkItem, 
    ChartResponse, 
    ChartType, 
    ChartSeries, 
    ChartDataPoint,
    TaskStatus
)

class CapacityCalculator:
    """Calculates capacity planning data."""
    
    DEFAULT_WEEKLY_CAPACITY = 40.0
    
    @classmethod
    def calculate(
        cls,
        work_items: List[WorkItem],
        team_members: List[str],
        start_date: Optional[date] = None,
        weeks: int = 12
    ) -> ChartResponse:
        """
        Calculate capacity vs demand chart.
        
        Args:
            work_items: List of all active work items
            team_members: List of unique assignee IDs
            start_date: Start date for the chart (default: today)
            weeks: Number of weeks to project
            
        Returns:
            ChartResponse with capacity data
        """
        if not start_date:
            start_date = date.today()
            
        # Align start_date to Monday of current week
        days_to_monday = start_date.weekday()
        week_start = start_date - timedelta(days=days_to_monday)
        
        # Initialize weeks
        week_buckets = []
        for i in range(weeks):
            w_start = week_start + timedelta(weeks=i)
            w_end = w_start + timedelta(days=6)
            week_buckets.append({
                "start": w_start,
                "end": w_end,
                "label": f"Week {w_start.strftime('%V')}",
                "demand_by_assignee": defaultdict(float),
                "total_demand": 0.0
            })
            
        # Total available capacity (line)
        # capacity = num_team_members * 40h
        team_size = len(team_members) if team_members else 1 # Avoid 0 capacity if unknown
        total_capacity = team_size * cls.DEFAULT_WEEKLY_CAPACITY
        
        # Bucket tasks
        for item in work_items:
            # Skip done tasks (capacity planning is for future)
            if item.status == TaskStatus.DONE:
                continue
                
            # Skip items without due date
            current_due_date = item.due_date
            if not current_due_date:
                continue
                
            # Find the week bucket for this due date
            # simple assumption: consumption is allocated to the due date week
            days_diff = (current_due_date - week_start).days
            week_idx = days_diff // 7
            
            if 0 <= week_idx < weeks:
                bucket = week_buckets[week_idx]
                hours = item.estimated_hours or 0.0
                if hours == 0 and item.story_points:
                     hours = float(item.story_points) * 8.0 # Fallback conversion
                     
                assignee = item.assigned_to or "Unassigned"
                bucket["demand_by_assignee"][assignee] += hours
                bucket["total_demand"] += hours
        
        # Collect all assignees found in demand
        all_assignees = set()
        for bucket in week_buckets:
            all_assignees.update(bucket["demand_by_assignee"].keys())
            
        series = []
        
        # Capacity Line series
        capacity_series = ChartSeries(
            name="Total Capacity",
            type="line",
            color="#000000", # Black line
            data=[
                ChartDataPoint(
                    date=datetime.combine(b["start"], datetime.min.time()),
                    value=total_capacity,
                    label=b["label"]
                )
                for b in week_buckets
            ],
            metadata={"is_reference_line": True}
        )
        series.append(capacity_series)
        
        # Demand Bars (per assignee)
        # Predictable color palette
        colors = ["#8884d8", "#82ca9d", "#ffc658", "#ff7300", "#0088fe", "#00c49f", "#ff8042", "#a4de6c"]
        
        sorted_assignees = sorted(list(all_assignees))
        for i, assignee in enumerate(sorted_assignees):
            color = colors[i % len(colors)]
            assignee_series = ChartSeries(
                name=assignee,
                type="bar", 
                color=color,
                data=[],
                metadata={"stackId": "demand"}
            )
            
            for bucket in week_buckets:
                val = bucket["demand_by_assignee"].get(assignee, 0.0)
                assignee_series.data.append(
                    ChartDataPoint(
                        date=datetime.combine(bucket["start"], datetime.min.time()),
                        value=val,
                        label=bucket["label"]
                    )
                )
            series.append(assignee_series)
            
        return ChartResponse(
            chart_type=ChartType.CAPACITY,
            title="Resource Capacity Planning",
            series=series,
            metadata={
                "weeks": weeks,
                "start_date": start_date.isoformat(),
                "total_capacity_per_week": total_capacity,
                "team_size": team_size,
                "metric": "hours"
            }
        )
