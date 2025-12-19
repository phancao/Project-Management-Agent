"""
Data models for analytics and chart generation.

These models provide a consistent structure for chart data that can be
easily serialized to JSON and consumed by frontends and AI agents.
"""

from datetime import datetime
from datetime import date as date_type
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class ChartType(str, Enum):
    """Supported chart types"""
    BURNDOWN = "burndown"
    BURNUP = "burnup"
    VELOCITY = "velocity"
    CFD = "cfd"  # Cumulative Flow Diagram
    CYCLE_TIME = "cycle_time"
    CONTROL_CHART = "control_chart"
    DISTRIBUTION = "distribution"
    TREND = "trend"
    SPRINT_REPORT = "sprint_report"
    EPIC_PROGRESS = "epic_progress"
    RELEASE_BURNDOWN = "release_burndown"


class ChartDataPoint(BaseModel):
    """A single data point in a chart series"""
    date: Optional[datetime] = Field(None, description="Timestamp for time-series data")
    value: float = Field(..., description="Numeric value")
    label: Optional[str] = Field(None, description="Text label for categorical data")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ChartSeries(BaseModel):
    """A data series in a chart (e.g., 'Actual' line in burndown)"""
    name: str = Field(..., description="Series name")
    data: List[ChartDataPoint] = Field(default_factory=list, description="Data points")
    color: Optional[str] = Field(None, description="Hex color code")
    type: Optional[str] = Field(None, description="Chart type for this series (line, bar, area)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class ChartResponse(BaseModel):
    """Standard response format for all chart endpoints"""
    chart_type: ChartType = Field(..., description="Type of chart")
    title: str = Field(..., description="Chart title")
    series: List[ChartSeries] = Field(default_factory=list, description="Data series")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chart metadata and summary statistics")
    generated_at: datetime = Field(default_factory=datetime.now, description="When this chart was generated")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Domain models for analytics calculations

class TaskStatus(str, Enum):
    """Task status states"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"


class WorkItemType(str, Enum):
    """Types of work items"""
    STORY = "story"
    BUG = "bug"
    TASK = "task"
    EPIC = "epic"
    SUBTASK = "subtask"


class Priority(str, Enum):
    """Work item priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class WorkItem(BaseModel):
    """Represents a work item (task, story, bug, etc.)"""
    id: str = Field(..., description="Unique identifier")
    title: str = Field(..., description="Work item title")
    type: WorkItemType = Field(..., description="Type of work item")
    status: TaskStatus = Field(..., description="Current status")
    priority: Priority = Field(default=Priority.MEDIUM, description="Priority level")
    story_points: Optional[float] = Field(None, description="Story points estimate")
    estimated_hours: Optional[float] = Field(None, description="Estimated hours")
    actual_hours: Optional[float] = Field(None, description="Actual hours spent")
    assigned_to: Optional[str] = Field(None, description="Assignee name")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    component: Optional[str] = Field(None, description="Component/module name")


class TaskTransition(BaseModel):
    """Represents a status transition for a task"""
    task_id: str = Field(..., description="Task identifier")
    from_status: TaskStatus = Field(..., description="Previous status")
    to_status: TaskStatus = Field(..., description="New status")
    transitioned_at: datetime = Field(..., description="When the transition occurred")
    transitioned_by: Optional[str] = Field(None, description="Who made the transition")


class SprintData(BaseModel):
    """Complete data for a sprint"""
    id: str = Field(..., description="Sprint identifier")
    name: str = Field(..., description="Sprint name")
    project_id: str = Field(..., description="Parent project ID")
    start_date: date_type = Field(..., description="Sprint start date")
    end_date: date_type = Field(..., description="Sprint end date")
    status: Literal["planning", "active", "completed", "cancelled"] = Field(..., description="Sprint status")
    
    # Capacity and commitment
    planned_points: Optional[float] = Field(None, description="Planned story points")
    completed_points: Optional[float] = Field(None, description="Completed story points")
    capacity_hours: Optional[float] = Field(None, description="Team capacity in hours")
    
    # Work items
    work_items: List[WorkItem] = Field(default_factory=list, description="All work items in sprint")
    
    # Scope changes
    added_items: List[WorkItem] = Field(default_factory=list, description="Items added after sprint start")
    removed_items: List[WorkItem] = Field(default_factory=list, description="Items removed during sprint")
    
    # Team
    team_members: List[str] = Field(default_factory=list, description="Team member names")

    class Config:
        json_encoders = {
            date_type: lambda v: v.isoformat()
        }


class VelocityDataPoint(BaseModel):
    """Data point for velocity chart"""
    sprint_name: str = Field(..., description="Sprint identifier/name")
    sprint_number: int = Field(..., description="Sprint sequence number")
    committed: float = Field(..., description="Committed story points")
    completed: float = Field(..., description="Completed story points")
    carry_over: Optional[float] = Field(None, description="Carried over from previous sprint")


class CycleTimeDataPoint(BaseModel):
    """Data point for cycle time analysis"""
    item_id: str = Field(..., description="Work item identifier")
    item_title: str = Field(..., description="Work item title")
    item_type: WorkItemType = Field(..., description="Type of work item")
    started_at: datetime = Field(..., description="When work started")
    completed_at: datetime = Field(..., description="When work completed")
    cycle_time_days: float = Field(..., description="Cycle time in days")
    lead_time_days: Optional[float] = Field(None, description="Lead time in days")


class DistributionData(BaseModel):
    """Data for work distribution charts"""
    category: str = Field(..., description="Distribution category (assignee, priority, type, etc.)")
    distribution: Dict[str, int] = Field(..., description="Item counts by category value")
    total: int = Field(..., description="Total number of items")


class TrendDataPoint(BaseModel):
    """Data point for trend analysis"""
    date: date_type = Field(..., description="Date of the data point")
    created: int = Field(default=0, description="Items created")
    resolved: int = Field(default=0, description="Items resolved")
    open: int = Field(default=0, description="Items still open")
    net_change: int = Field(default=0, description="Net change (created - resolved)")

    class Config:
        json_encoders = {
            date_type: lambda v: v.isoformat()
        }


class SprintReport(BaseModel):
    """Comprehensive sprint report"""
    sprint_id: str
    sprint_name: str
    duration: Dict[str, Any]  # start, end, days
    commitment: Dict[str, Any]  # planned, completed, completion_rate
    scope_changes: Dict[str, Any]  # added, removed, net_change
    work_breakdown: Dict[str, int]  # by type
    team_performance: Dict[str, float]  # velocity, capacity_utilized
    highlights: List[str]  # Key achievements
    concerns: List[str]  # Issues or blockers
    metadata: Dict[str, Any]

