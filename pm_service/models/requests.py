# PM Service Request Models
"""
Pydantic models for API request validation.
"""

from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ListProjectsRequest(BaseModel):
    """Request for listing projects."""
    user_id: Optional[str] = None
    provider_id: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class ListTasksRequest(BaseModel):
    """Request for listing tasks."""
    project_id: Optional[str] = None
    sprint_id: Optional[str] = None
    assignee_id: Optional[str] = None
    status: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class CreateTaskRequest(BaseModel):
    """Request for creating a task."""
    project_id: str
    title: str
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    sprint_id: Optional[str] = None
    story_points: Optional[float] = None
    priority: Optional[str] = None
    task_type: Optional[str] = None
    parent_id: Optional[str] = None


class UpdateTaskRequest(BaseModel):
    """Request for updating a task."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    sprint_id: Optional[str] = None
    story_points: Optional[float] = None
    priority: Optional[str] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)


class AddCommentRequest(BaseModel):
    """Request for adding a comment to a task."""
    content: str


class LogTimeRequest(BaseModel):
    """Request for logging time on a task."""
    hours: float = Field(gt=0)
    date: date
    comment: Optional[str] = None
    activity_type: Optional[str] = None


class ListSprintsRequest(BaseModel):
    """Request for listing sprints."""
    project_id: Optional[str] = None
    status: Optional[str] = None  # active, closed, future
    limit: int = Field(default=50, ge=1, le=100)


class SprintReportRequest(BaseModel):
    """Request for sprint report."""
    project_id: str
    sprint_id: str


class BurndownRequest(BaseModel):
    """Request for burndown chart data."""
    project_id: str
    sprint_id: str


class VelocityRequest(BaseModel):
    """Request for velocity chart data."""
    project_id: str
    num_sprints: int = Field(default=5, ge=1, le=20)


class ProjectHealthRequest(BaseModel):
    """Request for project health metrics."""
    project_id: str


class ProviderSyncRequest(BaseModel):
    """Request for syncing provider from backend."""
    backend_provider_id: str
    provider_type: str
    name: str
    base_url: str
    api_key: Optional[str] = None
    api_token: Optional[str] = None
    username: Optional[str] = None
    is_active: bool = True
    additional_config: Optional[dict[str, Any]] = None

