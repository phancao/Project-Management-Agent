# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Issue Trend Analysis Calculator

Tracks how issues are created and resolved over time.
Helps identify if the backlog is growing or shrinking.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import defaultdict

from src.analytics.models import ChartResponse, ChartSeries, ChartDataPoint, ChartType


def calculate_issue_trend(
    work_items: List[Dict[str, Any]],
    start_date: datetime,
    end_date: datetime
) -> ChartResponse:
    """
    Calculate issue trend (created vs resolved over time).
    
    Args:
        work_items: List of work items with 'created_date', 'completion_date', 'type'
        start_date: Start date for the analysis
        end_date: End date for the analysis
    
    Returns:
        ChartResponse with trend data
    """
    # Generate date range
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date.date())
        current_date += timedelta(days=1)
    
    # Count created and resolved items per day
    created_by_date: Dict[Any, int] = defaultdict(int)
    resolved_by_date: Dict[Any, int] = defaultdict(int)
    
    for item in work_items:
        # Count created
        if item.get("created_date"):
            try:
                created_date = datetime.fromisoformat(item["created_date"]).date()
                if start_date.date() <= created_date <= end_date.date():
                    created_by_date[created_date] += 1
            except (ValueError, TypeError):
                pass
        
        # Count resolved
        if item.get("completion_date"):
            try:
                completion_date = datetime.fromisoformat(item["completion_date"]).date()
                if start_date.date() <= completion_date <= end_date.date():
                    resolved_by_date[completion_date] += 1
            except (ValueError, TypeError):
                pass
    
    # Build time series data
    created_series: List[ChartDataPoint] = []
    resolved_series: List[ChartDataPoint] = []
    net_series: List[ChartDataPoint] = []
    cumulative_series: List[ChartDataPoint] = []
    
    cumulative_net = 0
    
    for date in date_range:
        created_count = created_by_date[date]
        resolved_count = resolved_by_date[date]
        net_change = created_count - resolved_count
        cumulative_net += net_change
        
        date_str = date.isoformat()
        label = date.strftime("%b %d")
        
        created_series.append(ChartDataPoint(
            date=datetime.combine(date, datetime.min.time()),
            value=created_count,
            label=label
        ))
        
        resolved_series.append(ChartDataPoint(
            date=datetime.combine(date, datetime.min.time()),
            value=resolved_count,
            label=label
        ))
        
        net_series.append(ChartDataPoint(
            date=datetime.combine(date, datetime.min.time()),
            value=net_change,
            label=label
        ))
        
        cumulative_series.append(ChartDataPoint(
            date=datetime.combine(date, datetime.min.time()),
            value=cumulative_net,
            label=label
        ))
    
    # Calculate statistics
    total_created = sum(created_by_date.values())
    total_resolved = sum(resolved_by_date.values())
    net_change_total = total_created - total_resolved
    
    avg_created_per_day = total_created / len(date_range) if date_range else 0
    avg_resolved_per_day = total_resolved / len(date_range) if date_range else 0
    
    # Generate insights
    insights = generate_trend_insights(
        total_created, total_resolved, net_change_total,
        avg_created_per_day, avg_resolved_per_day, cumulative_net
    )
    
    return ChartResponse(
        chart_type=ChartType.TREND,
        title="Issue Trend Analysis",
        series=[
            ChartSeries(
                name="Created",
                data=created_series,
                color="#3b82f6",  # Blue
                type="line"
            ),
            ChartSeries(
                name="Resolved",
                data=resolved_series,
                color="#10b981",  # Green
                type="line"
            ),
            ChartSeries(
                name="Net Change",
                data=net_series,
                color="#f59e0b",  # Orange
                type="bar"
            ),
            ChartSeries(
                name="Cumulative Net",
                data=cumulative_series,
                color="#ef4444",  # Red
                type="line"
            ),
        ],
        metadata={
            "total_created": total_created,
            "total_resolved": total_resolved,
            "net_change": net_change_total,
            "avg_created_per_day": round(avg_created_per_day, 1),
            "avg_resolved_per_day": round(avg_resolved_per_day, 1),
            "cumulative_net": cumulative_net,
            "insights": insights,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        generated_at=datetime.now()
    )


def generate_trend_insights(
    total_created: int,
    total_resolved: int,
    net_change: int,
    avg_created: float,
    avg_resolved: float,
    cumulative_net: int
) -> List[str]:
    """Generate insights based on issue trends"""
    insights = []
    
    # Overall trend
    if net_change > 0:
        insights.append(
            f"⚠️ Backlog is growing: {net_change} more issues created than resolved in this period."
        )
    elif net_change < 0:
        insights.append(
            f"✅ Backlog is shrinking: {abs(net_change)} more issues resolved than created in this period."
        )
    else:
        insights.append(
            "➡️ Backlog is stable: Issues are being resolved at the same rate they're created."
        )
    
    # Creation vs resolution rate
    if avg_created > avg_resolved * 1.2:
        insights.append(
            f"Issues are being created faster ({avg_created:.1f}/day) than resolved ({avg_resolved:.1f}/day). "
            "Consider increasing team capacity or reducing scope."
        )
    elif avg_resolved > avg_created * 1.2:
        insights.append(
            f"Great progress! Team is resolving issues ({avg_resolved:.1f}/day) faster than they're created ({avg_created:.1f}/day)."
        )
    
    # Cumulative assessment
    if cumulative_net > 20:
        insights.append(
            f"📈 Cumulative backlog has grown by {cumulative_net} issues. Review priorities and capacity."
        )
    elif cumulative_net < -20:
        insights.append(
            f"📉 Cumulative backlog has decreased by {abs(cumulative_net)} issues. Excellent progress!"
        )
    
    # Productivity insight
    if total_resolved > 0:
        resolution_rate = (total_resolved / (total_created + total_resolved)) * 100
        insights.append(
            f"Resolution rate: {resolution_rate:.0f}% of all activity was resolving issues."
        )
    
    return insights

