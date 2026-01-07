"""
Cumulative Flow Diagram (CFD) Calculator

Generates CFD data showing cumulative work items in different states over time.
Useful for identifying bottlenecks, WIP limits, and flow efficiency.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from ..models import ChartResponse, ChartSeries, ChartDataPoint, ChartType


def _normalize_datetime(dt: datetime) -> datetime:
    """Ensure datetime is timezone-naive for consistent comparison."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        # Convert to UTC then remove timezone info
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


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
    
    # Normalize dates to timezone-naive
    start_date = _normalize_datetime(start_date)
    end_date = _normalize_datetime(end_date)
    
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
            
            # Add to count for this item's current status only
            # (CFD shows cumulative count of items in each status, not across statuses)
            if item_status in statuses:
                cumulative_counts[item_status] += 1
        
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
    # Comprehensive color mapping for various PM provider statuses
    colors = {
        # Completed/Done states - Green shades
        "Done": "#10b981",         # Emerald green
        "Closed": "#059669",       # Darker green
        "Passed": "#34d399",       # Light green
        "Resolved": "#10b981",     # Emerald green
        "Completed": "#059669",    # Darker green
        
        # In Progress states - Orange/Amber shades
        "In Progress": "#f59e0b",  # Amber
        "In progress": "#f59e0b",  # Amber (lowercase variant)
        "Developed": "#f97316",    # Orange
        "Development": "#f97316",  # Orange
        "Ready4SIT": "#fb923c",    # Light orange
        "Testing": "#fbbf24",      # Yellow-orange
        
        # Review/Verification states - Blue shades
        "In Review": "#3b82f6",    # Blue
        "Review": "#3b82f6",       # Blue
        "Confirmed": "#60a5fa",    # Light blue
        "Verified": "#2563eb",     # Darker blue
        "Specified": "#818cf8",    # Indigo/purple-blue
        
        # New/Todo states - Cyan/Teal shades
        "New": "#06b6d4",          # Cyan
        "To Do": "#94a3b8",        # Slate gray
        "Todo": "#94a3b8",         # Slate gray (variant)
        "Open": "#22d3ee",         # Light cyan
        "Backlog": "#a5b4fc",      # Light indigo
        
        # Blocked/Hold states - Red/Pink shades
        "On hold": "#f43f5e",      # Rose
        "On Hold": "#f43f5e",      # Rose (variant)
        "Blocked": "#ef4444",      # Red
        "Rejected": "#dc2626",     # Darker red
        
        # Planning states - Purple shades
        "Planned": "#a855f7",      # Purple
        "Planning": "#c084fc",     # Light purple
        "Draft": "#d8b4fe",        # Very light purple
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
    # Normalize the comparison date
    date = _normalize_datetime(date)
    
    # If item has status_history, use it
    status_history = item.get("status_history", [])
    if status_history:
        # Find the most recent status change before or on this date
        applicable_status = None
        for change in status_history:
            change_date = change.get("date")
            if isinstance(change_date, str):
                change_date = datetime.fromisoformat(change_date.replace("Z", "+00:00"))
            change_date = _normalize_datetime(change_date)
            
            if change_date and change_date <= date:
                applicable_status = change.get("status")
            elif change_date:
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
    
    # Normalize dates
    created_date = _normalize_datetime(created_date)
    completion_date = _normalize_datetime(completion_date)
    
    # If not yet created, return None
    if created_date and date < created_date:
        return "Not Started"
    
    # If completed, return Done
    if completion_date and date >= completion_date:
        return "Done"
    
    # Otherwise, use current status or default
    return item.get("status", "To Do")

