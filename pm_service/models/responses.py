# PM Service Response Models
"""
Pydantic models for API responses.
"""

from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    providers_count: int
    database_connected: bool


class ProjectResponse(BaseModel):
    """Project response."""
    id: str
    name: str
    key: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    provider_id: str
    provider_name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None


class TaskResponse(BaseModel):
    """Task response."""
    id: str
    title: str
    description: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    project_id: str
    sprint_id: Optional[str] = None
    story_points: Optional[float] = None
    priority: Optional[str] = None
    task_type: Optional[str] = None
    progress: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    due_date: Optional[date] = None
    provider_id: str
    provider_name: str
    metadata: Optional[dict[str, Any]] = None


class SprintResponse(BaseModel):
    """Sprint response."""
    id: str
    name: str
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    goal: Optional[str] = None
    project_id: str
    provider_id: str
    provider_name: str
    metadata: Optional[dict[str, Any]] = None


class UserResponse(BaseModel):
    """User response."""
    id: str
    name: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    role: Optional[str] = None
    provider_id: str
    provider_name: str


class CommentResponse(BaseModel):
    """Comment response."""
    id: str
    content: str
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    created_at: Optional[datetime] = None


class TimeEntryResponse(BaseModel):
    """Time entry response."""
    id: str
    hours: float
    date: date
    comment: Optional[str] = None
    activity_type: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None


class ListResponse(BaseModel):
    """Generic list response with pagination."""
    items: list[Any]
    total: int
    returned: int
    offset: int = 0
    limit: int = 100


class SprintReportResponse(BaseModel):
    """Sprint report response."""
    sprint_id: str
    sprint_name: str
    status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    # Metrics
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    todo_tasks: int
    
    total_story_points: float
    completed_story_points: float
    
    completion_rate: float
    velocity: float
    
    # Team
    team_size: int
    team_members: list[str]
    
    # Scope changes
    added_tasks: int
    removed_tasks: int
    scope_change_percent: float


class BurndownDataPoint(BaseModel):
    """Single data point for burndown chart."""
    date: date
    ideal_remaining: float
    actual_remaining: float
    completed: float


class BurndownResponse(BaseModel):
    """Burndown chart response."""
    sprint_id: str
    sprint_name: str
    start_date: date
    end_date: date
    total_points: float
    data_points: list[BurndownDataPoint]


class VelocityDataPoint(BaseModel):
    """Single data point for velocity chart."""
    sprint_id: str
    sprint_name: str
    committed_points: float
    completed_points: float
    completion_rate: float


class VelocityResponse(BaseModel):
    """Velocity chart response."""
    project_id: str
    sprints: list[VelocityDataPoint]
    average_velocity: float
    trend: str  # "increasing", "decreasing", "stable"


class ProjectHealthResponse(BaseModel):
    """Project health response."""
    project_id: str
    project_name: str
    
    # Overall health
    health_score: float  # 0-100
    health_status: str  # "healthy", "at_risk", "critical"
    
    # Sprint health
    current_sprint: Optional[str] = None
    sprint_progress: float
    sprint_on_track: bool
    
    # Backlog health
    total_backlog_items: int
    groomed_items: int
    unestimated_items: int
    
    # Team health
    team_size: int
    average_velocity: float
    velocity_trend: str
    
    # Recommendations
    recommendations: list[str]


class ProviderResponse(BaseModel):
    """Provider configuration response."""
    id: str
    name: str
    provider_type: str
    base_url: str
    is_active: bool
    is_connected: bool
    last_sync_at: Optional[datetime] = None
    error_message: Optional[str] = None
    additional_config: Optional[dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None

