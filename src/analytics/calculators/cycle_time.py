# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Cycle Time / Control Chart Calculator

Calculates cycle time metrics for work items, showing how long items take
from start to completion. Useful for identifying bottlenecks and predicting
delivery times.
"""

from datetime import datetime
from typing import List, Dict, Any
import statistics

from src.analytics.models import ChartResponse, ChartSeries, ChartDataPoint, ChartType


def calculate_cycle_time(work_items: List[Dict[str, Any]]) -> ChartResponse:
    """
    Calculates cycle time metrics for completed work items.
    
    Cycle time is the time from when work starts to when it's completed.
    
    Args:
        work_items: List of work items with 'start_date', 'completion_date', 
                   'title', 'type', 'id'
    
    Returns:
        ChartResponse with cycle time data and percentile lines
    """
    # Filter completed items with valid dates
    completed_items = []
    for item in work_items:
        if not item.get("completion_date") or not item.get("start_date"):
            continue
        
        try:
            start = datetime.fromisoformat(item["start_date"])
            completion = datetime.fromisoformat(item["completion_date"])
            
            if completion > start:
                cycle_time_days = (completion - start).days
                completed_items.append({
                    "id": item.get("id", "unknown"),
                    "title": item.get("title", "Untitled"),
                    "type": item.get("type", "task"),
                    "start_date": start,
                    "completion_date": completion,
                    "cycle_time_days": cycle_time_days,
                })
        except (ValueError, TypeError):
            continue
    
    if not completed_items:
        # Return empty chart if no data
        return ChartResponse(
            chart_type=ChartType.CYCLE_TIME,
            title="Cycle Time / Control Chart",
            series=[],
            metadata={
                "total_items": 0,
                "avg_cycle_time": 0,
                "median_cycle_time": 0,
                "percentile_50": 0,
                "percentile_85": 0,
                "percentile_95": 0,
            },
            generated_at=datetime.now()
        )
    
    # Sort by completion date
    completed_items.sort(key=lambda x: x["completion_date"])
    
    # Extract cycle times
    cycle_times = [item["cycle_time_days"] for item in completed_items]
    
    # Calculate statistics
    avg_cycle_time = statistics.mean(cycle_times)
    median_cycle_time = statistics.median(cycle_times)
    
    # Calculate percentiles
    sorted_times = sorted(cycle_times)
    n = len(sorted_times)
    
    def percentile(p: float) -> float:
        """Calculate percentile value"""
        k = (n - 1) * p
        f = int(k)
        c = k - f
        if f + 1 < n:
            return sorted_times[f] + c * (sorted_times[f + 1] - sorted_times[f])
        return sorted_times[f]
    
    p50 = percentile(0.50)
    p85 = percentile(0.85)
    p95 = percentile(0.95)
    
    # Create scatter plot data points
    scatter_data: List[ChartDataPoint] = []
    for i, item in enumerate(completed_items):
        scatter_data.append(ChartDataPoint(
            date=item["completion_date"],
            value=item["cycle_time_days"],
            label=item["title"][:30],  # Truncate long titles
            metadata={
                "id": item["id"],
                "type": item["type"],
                "full_title": item["title"],
            }
        ))
    
    # Create percentile lines (horizontal lines across the chart)
    percentile_50_line: List[ChartDataPoint] = []
    percentile_85_line: List[ChartDataPoint] = []
    percentile_95_line: List[ChartDataPoint] = []
    
    for i, item in enumerate(completed_items):
        percentile_50_line.append(ChartDataPoint(
            date=item["completion_date"],
            value=p50,
            label=f"50th: {p50:.1f}d"
        ))
        percentile_85_line.append(ChartDataPoint(
            date=item["completion_date"],
            value=p85,
            label=f"85th: {p85:.1f}d"
        ))
        percentile_95_line.append(ChartDataPoint(
            date=item["completion_date"],
            value=p95,
            label=f"95th: {p95:.1f}d"
        ))
    
    # Identify outliers (items above 95th percentile)
    outliers = [
        item for item in completed_items 
        if item["cycle_time_days"] > p95
    ]
    
    # Create series
    series = [
        ChartSeries(
            name="Cycle Time",
            data=scatter_data,
            color="#3b82f6",  # Blue
            type="scatter"
        ),
        ChartSeries(
            name="50th Percentile",
            data=percentile_50_line,
            color="#10b981",  # Green
            type="line"
        ),
        ChartSeries(
            name="85th Percentile",
            data=percentile_85_line,
            color="#f59e0b",  # Orange
            type="line"
        ),
        ChartSeries(
            name="95th Percentile",
            data=percentile_95_line,
            color="#ef4444",  # Red
            type="line"
        ),
    ]
    
    return ChartResponse(
        chart_type=ChartType.CYCLE_TIME,
        title="Cycle Time / Control Chart",
        series=series,
        metadata={
            "total_items": len(completed_items),
            "avg_cycle_time": round(avg_cycle_time, 1),
            "median_cycle_time": round(median_cycle_time, 1),
            "percentile_50": round(p50, 1),
            "percentile_85": round(p85, 1),
            "percentile_95": round(p95, 1),
            "outliers": [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "cycle_time_days": item["cycle_time_days"],
                }
                for item in outliers
            ],
            "insights": generate_cycle_time_insights(
                avg_cycle_time, median_cycle_time, p85, p95, len(outliers), len(completed_items)
            ),
        },
        generated_at=datetime.now()
    )


def generate_cycle_time_insights(
    avg: float, median: float, p85: float, p95: float, 
    outlier_count: int, total_count: int
) -> List[str]:
    """Generate insights based on cycle time metrics"""
    insights = []
    
    # Average vs Median
    if avg > median * 1.3:
        insights.append(
            f"Average ({avg:.1f}d) is significantly higher than median ({median:.1f}d), "
            "indicating some items take much longer than typical."
        )
    
    # Predictability
    if p85 < median * 1.5:
        insights.append(
            "Good predictability: 85% of items complete within a reasonable timeframe."
        )
    else:
        insights.append(
            "High variability: Consider breaking down larger items for more predictable delivery."
        )
    
    # Outliers
    if outlier_count > 0:
        outlier_pct = (outlier_count / total_count) * 100
        insights.append(
            f"{outlier_count} outlier(s) detected ({outlier_pct:.0f}%) - "
            "review these items for blockers or scope issues."
        )
    
    # Cycle time assessment
    if median <= 3:
        insights.append("Excellent cycle time! Items are flowing quickly through the system.")
    elif median <= 7:
        insights.append("Good cycle time. Consider ways to reduce it further.")
    else:
        insights.append(
            "High cycle time detected. Look for bottlenecks and ways to break down work."
        )
    
    return insights

