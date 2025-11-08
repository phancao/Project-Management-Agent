"""
Cumulative Flow Diagram (CFD) Calculator

Generates CFD data showing cumulative work items in different states over time.
Useful for identifying bottlenecks, WIP limits, and flow efficiency.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from ..models import ChartResponse, ChartSeries, ChartDataPoint, ChartType


def calculate_cfd(
    work_items: List[Dict[str, Any]],
    start_date: datetime,
    end_date: datetime,
    statuses: List[str] = None
) -> ChartResponse:
    """
    Calculate Cumulative Flow Diagram data.
    
    Args:
        work_items: List of work items with status history
        start_date: Start date for the CFD
        end_date: End date for the CFD
        statuses: List of status names to track (in order)
        
    Returns:
        ChartResponse with CFD data
    """
    
    # Default statuses if not provided
    if statuses is None:
        statuses = ["To Do", "In Progress", "In Review", "Done"]
    
    # Generate date range
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date)
        current_date += timedelta(days=1)
    
    # Initialize cumulative counts for each status
    status_data: Dict[str, List[ChartDataPoint]] = {
        status: [] for status in statuses
    }
    
    # For each date, count cumulative items in each status
    for date in date_range:
        cumulative_counts = {status: 0 for status in statuses}
        
        for item in work_items:
            # Determine item's status on this date
            item_status = _get_status_on_date(item, date)
            
            # Add to cumulative count for this status and all "earlier" statuses
            status_index = statuses.index(item_status) if item_status in statuses else -1
            if status_index >= 0:
                for i in range(status_index + 1):
                    cumulative_counts[statuses[i]] += 1
        
        # Add data points for each status
        for status in statuses:
            status_data[status].append(
                ChartDataPoint(
                    date=date,
                    value=float(cumulative_counts[status]),
                    label=date.strftime("%Y-%m-%d")
                )
            )
    
    # Create series (in reverse order so "Done" is at bottom of stacked area)
    series = []
    colors = {
        "Done": "#10b981",      # Green
        "In Review": "#3b82f6", # Blue
        "In Progress": "#f59e0b", # Orange
        "To Do": "#94a3b8"      # Gray
    }
    
    for status in reversed(statuses):
        series.append(
            ChartSeries(
                name=status,
                data=status_data[status],
                color=colors.get(status, "#6b7280"),
                type="area"
            )
        )
    
    # Calculate metadata
    latest_counts = {status: status_data[status][-1].value if status_data[status] else 0 for status in statuses}
    total_items = sum(latest_counts.values())
    
    # Calculate average WIP (Work in Progress)
    wip_over_time = []
    for i in range(len(date_range)):
        wip = 0
        for status in ["In Progress", "In Review"]:
            if status in status_data and i < len(status_data[status]):
                wip += status_data[status][i].value
        wip_over_time.append(wip)
    
    avg_wip = sum(wip_over_time) / len(wip_over_time) if wip_over_time else 0
    
    # Estimate cycle time (days from start to done)
    done_items = [item for item in work_items if _get_status_on_date(item, end_date) == "Done"]
    cycle_times = []
    for item in done_items:
        start = item.get("start_date")
        end = item.get("completion_date")
        if start and end:
            if isinstance(start, str):
                start = datetime.fromisoformat(start.replace("Z", "+00:00"))
            if isinstance(end, str):
                end = datetime.fromisoformat(end.replace("Z", "+00:00"))
            cycle_times.append((end - start).days)
    
    avg_cycle_time = sum(cycle_times) / len(cycle_times) if cycle_times else 0
    
    # Identify bottlenecks (statuses with high accumulation)
    bottlenecks = []
    for status in statuses:
        if status not in ["To Do", "Done"]:
            count = latest_counts.get(status, 0)
            if count > avg_wip * 0.5:  # More than 50% of average WIP
                bottlenecks.append(status)
    
    metadata = {
        "total_items": int(total_items),
        "avg_wip": round(avg_wip, 1),
        "avg_cycle_time_days": round(avg_cycle_time, 1),
        "bottlenecks": bottlenecks,
        "status_distribution": {
            status: int(latest_counts.get(status, 0))
            for status in statuses
        },
        "flow_efficiency": round(
            (latest_counts.get("Done", 0) / total_items * 100) if total_items > 0 else 0,
            1
        )
    }
    
    return ChartResponse(
        chart_type=ChartType.CFD,
        title="Cumulative Flow Diagram",
        series=series,
        metadata=metadata,
        generated_at=datetime.now()
    )


def _get_status_on_date(item: Dict[str, Any], date: datetime) -> str:
    """
    Determine the status of a work item on a specific date.
    
    Args:
        item: Work item with status history
        date: Date to check
        
    Returns:
        Status name on that date
    """
    # If item has status_history, use it
    status_history = item.get("status_history", [])
    if status_history:
        # Find the most recent status change before or on this date
        applicable_status = None
        for change in status_history:
            change_date = change.get("date")
            if isinstance(change_date, str):
                change_date = datetime.fromisoformat(change_date.replace("Z", "+00:00"))
            
            if change_date <= date:
                applicable_status = change.get("status")
            else:
                break
        
        if applicable_status:
            return applicable_status
    
    # Fallback: use created_date and completion_date
    created_date = item.get("created_date")
    completion_date = item.get("completion_date")
    
    if isinstance(created_date, str):
        created_date = datetime.fromisoformat(created_date.replace("Z", "+00:00"))
    if isinstance(completion_date, str):
        completion_date = datetime.fromisoformat(completion_date.replace("Z", "+00:00"))
    
    # If not yet created, return None
    if created_date and date < created_date:
        return "Not Started"
    
    # If completed, return Done
    if completion_date and date >= completion_date:
        return "Done"
    
    # Otherwise, use current status or default
    return item.get("status", "To Do")

