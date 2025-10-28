"""
Database models for Project Management Agent

This module defines Pydantic models for database operations and API serialization.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class ProjectStatus(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    DEVELOPER = "developer"
    DESIGNER = "designer"
    TESTER = "tester"

# Base models
class BaseModelWithTimestamps(BaseModel):
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

# User models
class UserBase(BaseModel):
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="User full name")
    role: UserRole = Field(default=UserRole.DEVELOPER, description="User role")

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[UserRole] = None

class User(UserBase, BaseModelWithTimestamps):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)

# Project models
class ProjectBase(BaseModel):
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    domain: Optional[str] = Field(None, description="Project domain/industry")
    priority: Priority = Field(default=Priority.MEDIUM, description="Project priority")
    timeline_weeks: Optional[int] = Field(None, description="Project timeline in weeks")
    budget: Optional[float] = Field(None, description="Project budget")

class ProjectCreate(ProjectBase):
    goals: Optional[List[str]] = Field(default=[], description="Project goals")
    technologies: Optional[List[str]] = Field(default=[], description="Technologies to use")

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    status: Optional[ProjectStatus] = None
    priority: Optional[Priority] = None
    timeline_weeks: Optional[int] = None
    budget: Optional[float] = None

class Project(ProjectBase, BaseModelWithTimestamps):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    status: ProjectStatus = Field(default=ProjectStatus.PLANNING)
    created_by: uuid.UUID = Field(..., description="User ID who created the project")
    completed_at: Optional[datetime] = None

# Project goal models
class ProjectGoalBase(BaseModel):
    goal_text: str = Field(..., description="Goal description")
    priority: int = Field(default=1, description="Goal priority (1=highest)")

class ProjectGoalCreate(ProjectGoalBase):
    pass

class ProjectGoalUpdate(BaseModel):
    goal_text: Optional[str] = None
    priority: Optional[int] = None
    completed: Optional[bool] = None

class ProjectGoal(ProjectGoalBase, BaseModelWithTimestamps):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = Field(..., description="Project ID")
    completed: bool = Field(default=False)

# Team member models
class TeamMemberBase(BaseModel):
    role: str = Field(..., description="Role in the project")
    skills: List[str] = Field(default=[], description="List of skills")
    hourly_rate: Optional[float] = Field(None, description="Hourly rate")

class TeamMemberCreate(TeamMemberBase):
    user_id: uuid.UUID = Field(..., description="User ID")

class TeamMemberUpdate(BaseModel):
    role: Optional[str] = None
    skills: Optional[List[str]] = None
    hourly_rate: Optional[float] = None

class TeamMember(TeamMemberBase, BaseModelWithTimestamps):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = Field(..., description="User ID")
    project_id: uuid.UUID = Field(..., description="Project ID")
    joined_at: datetime = Field(default_factory=datetime.now)

# Task models
class TaskBase(BaseModel):
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    priority: Priority = Field(default=Priority.MEDIUM, description="Task priority")
    estimated_hours: Optional[float] = Field(None, description="Estimated hours to complete")
    due_date: Optional[datetime] = Field(None, description="Task due date")

class TaskCreate(TaskBase):
    parent_task_id: Optional[uuid.UUID] = Field(None, description="Parent task ID for subtasks")
    assigned_to: Optional[uuid.UUID] = Field(None, description="Team member assigned to task")

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[Priority] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    assigned_to: Optional[uuid.UUID] = None
    due_date: Optional[datetime] = None

class Task(TaskBase, BaseModelWithTimestamps):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = Field(..., description="Project ID")
    parent_task_id: Optional[uuid.UUID] = Field(None, description="Parent task ID")
    status: TaskStatus = Field(default=TaskStatus.TODO)
    actual_hours: float = Field(default=0.0, description="Actual hours spent")
    assigned_to: Optional[uuid.UUID] = Field(None, description="Team member assigned to task")
    completed_at: Optional[datetime] = None

# Task dependency models
class TaskDependencyBase(BaseModel):
    depends_on_task_id: uuid.UUID = Field(..., description="Task ID this task depends on")
    dependency_type: str = Field(default="finish_to_start", description="Type of dependency")

class TaskDependencyCreate(TaskDependencyBase):
    pass

class TaskDependency(TaskDependencyBase, BaseModelWithTimestamps):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    task_id: uuid.UUID = Field(..., description="Task ID")

# Research session models
class ResearchSessionBase(BaseModel):
    topic: str = Field(..., description="Research topic")
    research_type: str = Field(default="general", description="Type of research")
    findings: Optional[str] = Field(None, description="Research findings")

class ResearchSessionCreate(ResearchSessionBase):
    pass

class ResearchSessionUpdate(BaseModel):
    status: Optional[str] = None
    findings: Optional[str] = None
    sources: Optional[List[str]] = None

class ResearchSession(ResearchSessionBase, BaseModelWithTimestamps):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = Field(..., description="Project ID")
    status: str = Field(default="active", description="Research session status")
    research_data: Optional[Dict[str, Any]] = Field(default=None, description="Raw research data")
    sources: List[str] = Field(default=[], description="Research sources")
    completed_at: Optional[datetime] = None

# Knowledge base models
class KnowledgeBaseItemBase(BaseModel):
    content: str = Field(..., description="Knowledge content")
    content_type: str = Field(default="text", description="Type of content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    source_type: str = Field(..., description="Source type (research, project, manual)")
    source_id: Optional[uuid.UUID] = Field(None, description="Source ID")

class KnowledgeBaseItemCreate(KnowledgeBaseItemBase):
    pass

class KnowledgeBaseItemUpdate(BaseModel):
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class KnowledgeBaseItem(KnowledgeBaseItemBase, BaseModelWithTimestamps):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")

# Conversation models
class ConversationSessionBase(BaseModel):
    session_id: str = Field(..., description="Unique session identifier")
    current_state: str = Field(default="intent_detection", description="Current conversation state")
    intent: Optional[str] = Field(None, description="Detected intent")
    context_data: Optional[Dict[str, Any]] = Field(default=None, description="Conversation context")

class ConversationSessionCreate(ConversationSessionBase):
    user_id: uuid.UUID = Field(..., description="User ID")

class ConversationSession(ConversationSessionBase, BaseModelWithTimestamps):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = Field(..., description="User ID")
    ended_at: Optional[datetime] = None

class ConversationMessageBase(BaseModel):
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class ConversationMessageCreate(ConversationMessageBase):
    session_id: uuid.UUID = Field(..., description="Conversation session ID")

class ConversationMessage(ConversationMessageBase, BaseModelWithTimestamps):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    session_id: uuid.UUID = Field(..., description="Conversation session ID")

# Project template models
class ProjectTemplateBase(BaseModel):
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    domain: Optional[str] = Field(None, description="Template domain")
    template_data: Dict[str, Any] = Field(..., description="Template configuration data")
    is_public: bool = Field(default=False, description="Whether template is public")

class ProjectTemplateCreate(ProjectTemplateBase):
    pass

class ProjectTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None

class ProjectTemplate(ProjectTemplateBase, BaseModelWithTimestamps):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_by: uuid.UUID = Field(..., description="User ID who created the template")

# Project metrics models
class ProjectMetricBase(BaseModel):
    metric_type: str = Field(..., description="Type of metric")
    metric_value: float = Field(..., description="Metric value")
    metric_unit: Optional[str] = Field(None, description="Metric unit")

class ProjectMetricCreate(ProjectMetricBase):
    project_id: uuid.UUID = Field(..., description="Project ID")

class ProjectMetric(ProjectMetricBase, BaseModelWithTimestamps):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = Field(..., description="Project ID")
    recorded_at: datetime = Field(default_factory=datetime.now)

# Response models
class ProjectWithDetails(Project):
    goals: List[ProjectGoal] = Field(default=[])
    team_members: List[TeamMember] = Field(default=[])
    tasks: List[Task] = Field(default=[])
    research_sessions: List[ResearchSession] = Field(default=[])

class TaskWithDetails(Task):
    dependencies: List[TaskDependency] = Field(default=[])
    subtasks: List[Task] = Field(default=[])

# API response models
class APIResponse(BaseModel):
    success: bool = Field(default=True)
    message: str = Field(default="Success")
    data: Optional[Any] = Field(default=None)
    errors: Optional[List[str]] = Field(default=None)

class PaginatedResponse(BaseModel):
    items: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")
