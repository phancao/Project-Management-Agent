# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Work Distribution Calculator

Calculates how work is distributed across different dimensions:
- By Assignee (who is working on what)
- By Priority (high/medium/low priority breakdown)
- By Type (story/bug/task breakdown)
"""

from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict

from backend.analytics.models import ChartResponse, ChartSeries, ChartDataPoint, ChartType


def calculate_work_distribution(
    work_items: List[Dict[str, Any]],
    dimension: str = "assignee"
) -> ChartResponse:
    """
    Calculate work distribution across a specified dimension.
    
    Args:
        work_items: List of work items with 'assignee', 'priority', 'type', 'status', 'story_points'
        dimension: One of 'assignee', 'priority', 'type', 'status'
    
    Returns:
        ChartResponse with distribution data
    """
    if dimension not in ["assignee", "priority", "type", "status"]:
        raise ValueError(f"Invalid dimension: {dimension}. Must be one of: assignee, priority, type, status")
    
    # Count items and story points by dimension
    distribution: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "count": 0,
        "story_points": 0,
        "estimated_hours": 0,
        "completed": 0,
        "in_progress": 0,
        "todo": 0,
    })
    
    total_items = len(work_items)
    total_points = 0
    total_hours = 0
    
    for item in work_items:
        key = item.get(dimension, "Unassigned" if dimension == "assignee" else "Unknown")
        if not key or key == "":
            key = "Unassigned" if dimension == "assignee" else "Unknown"
        
        points = item.get("story_points", 0) or 0
        hours = item.get("estimated_hours", 0) or 0
        status = (item.get("status", "").lower() or "")
        
        distribution[key]["count"] += 1
        distribution[key]["story_points"] += points
        distribution[key]["estimated_hours"] += hours
        total_points += points
        total_hours += hours
        
        # Categorize by status
        if "done" in status or "closed" in status or "completed" in status:
            distribution[key]["completed"] += 1
        elif "progress" in status or "doing" in status:
            distribution[key]["in_progress"] += 1
        else:
            distribution[key]["todo"] += 1
    
    # Sort by count (descending)
    sorted_items = sorted(distribution.items(), key=lambda x: x[1]["count"], reverse=True)
    
    # Create chart data
    chart_data: List[ChartDataPoint] = []
    colors = [
        "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
        "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1"
    ]
    
    for i, (key, data) in enumerate(sorted_items):
        percentage = (data["count"] / total_items * 100) if total_items > 0 else 0
        points_percentage = (data["story_points"] / total_points * 100) if total_points > 0 else 0
        hours_percentage = (data["estimated_hours"] / total_hours * 100) if total_hours > 0 else 0
        
        chart_data.append(ChartDataPoint(
            value=data["count"],
            label=key,
            metadata={
                "story_points": data["story_points"],
                "estimated_hours": data["estimated_hours"],
                "percentage": round(percentage, 1),
                "points_percentage": round(points_percentage, 1),
                "hours_percentage": round(hours_percentage, 1),
                "completed": data["completed"],
                "in_progress": data["in_progress"],
                "todo": data["todo"],
                "color": colors[i % len(colors)],
            }
        ))
    
    # Generate insights
    insights = generate_distribution_insights(sorted_items, dimension, total_items)
    
    # Determine chart title
    titles = {
        "assignee": "Work Distribution by Assignee",
        "priority": "Work Distribution by Priority",
        "type": "Work Distribution by Type",
        "status": "Work Distribution by Status",
    }
    
    return ChartResponse(
        chart_type=ChartType.DISTRIBUTION,
        title=titles[dimension],
        series=[
            ChartSeries(
                name=dimension.capitalize(),
                data=chart_data,
                color="#3b82f6",
                type="pie"
            )
        ],
        metadata={
            "dimension": dimension,
            "total_items": total_items,
            "total_story_points": total_points,
            "total_estimated_hours": total_hours,
            "unique_values": len(distribution),
            "insights": insights,
        },
        generated_at=datetime.now()
    )


def generate_distribution_insights(
    sorted_items: List[tuple],
    dimension: str,
    total_items: int
) -> List[str]:
    """Generate insights based on work distribution"""
    insights = []
    
    if len(sorted_items) == 0:
        return ["No data available for analysis."]
    
    # Top contributor/category
    top_key, top_data = sorted_items[0]
    top_percentage = (top_data["count"] / total_items * 100) if total_items > 0 else 0
    
    if dimension == "assignee":
        insights.append(
            f"{top_key} has the most work with {top_data['count']} items ({top_percentage:.0f}%)."
        )
        
        # Check for workload imbalance
        if len(sorted_items) > 1:
            avg_items = total_items / len(sorted_items)
            if top_data["count"] > avg_items * 1.5:
                insights.append(
                    "⚠️ Workload imbalance detected. Consider redistributing work for better team balance."
                )
        
        # Check for unassigned work
        unassigned = next((data for key, data in sorted_items if key == "Unassigned"), None)
        if unassigned and unassigned["count"] > 0:
            insights.append(
                f"📌 {unassigned['count']} items are unassigned. Assign them to team members for better tracking."
            )
    
    elif dimension == "priority":
        insights.append(
            f"Most work is {top_key} priority ({top_percentage:.0f}%)."
        )
        
        # Check for high priority items
        high_priority = next((data for key, data in sorted_items if "high" in key.lower()), None)
        if high_priority and high_priority["count"] > total_items * 0.3:
            insights.append(
                "⚠️ High number of high-priority items. Review if all are truly urgent."
            )
    
    elif dimension == "type":
        insights.append(
            f"Most work items are {top_key}s ({top_percentage:.0f}%)."
        )
        
        # Check for bug ratio
        bugs = next((data for key, data in sorted_items if "bug" in key.lower()), None)
        if bugs:
            bug_ratio = bugs["count"] / total_items
            if bug_ratio > 0.3:
                insights.append(
                    f"🐛 Bugs represent {bug_ratio*100:.0f}% of work. Consider investing in quality improvements."
                )
    
    # General completion insight
    total_completed = sum(data["completed"] for _, data in sorted_items)
    completion_rate = (total_completed / total_items * 100) if total_items > 0 else 0
    insights.append(
        f"Overall completion rate: {completion_rate:.0f}% ({total_completed}/{total_items} items done)."
    )
    
    return insights

