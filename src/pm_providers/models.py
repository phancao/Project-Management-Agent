"""
Unified data models for PM providers

These models represent common entities across all PM systems,
abstracting away provider-specific differences.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum


class PMEntityType(str, Enum):
    """Types of PM entities"""
    PROJECT = "project"
    TASK = "task"
    SPRINT = "sprint"
    EPIC = "epic"
    MILESTONE = "milestone"


class PMStatus(str, Enum):
    """Common status values across PM systems"""
    # Project/General statuses
    PLANNING = "planning"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"
    
    # Task-specific
    TODO = "todo"
    DONE = "done"
    BLOCKED = "blocked"
    
    # Sprint-specific
    PLANNED = "planned"
    CLOSED = "closed"


class PMPriority(str, Enum):
    """Priority levels"""
    LOWEST = "lowest"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    HIGHEST = "highest"
    CRITICAL = "critical"


@dataclass
class PMUser:
    """Unified user/member representation"""
    id: Optional[str] = None
    name: str = ""
    email: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None  # Provider-specific data


@dataclass
class PMProject:
    """Unified project representation"""
    id: Optional[str] = None
    name: str = ""
    description: Optional[str] = None
    status: Optional[str] = None  # PMStatus
    priority: Optional[str] = None  # PMPriority
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    owner_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class PMTask:
    """Unified task/issue/work package representation"""
    id: Optional[str] = None
    title: str = ""
    description: Optional[str] = None
    status: Optional[str] = None  # PMStatus
    priority: Optional[str] = None  # PMPriority
    project_id: Optional[str] = None
    parent_task_id: Optional[str] = None  # For subtasks
    epic_id: Optional[str] = None  # Associated epic
    assignee_id: Optional[str] = None
    component_ids: Optional[List[str]] = None  # Associated components
    label_ids: Optional[List[str]] = None  # Associated labels
    sprint_id: Optional[str] = None  # Associated sprint
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class PMSprint:
    """Unified sprint/iteration representation"""
    id: Optional[str] = None
    name: str = ""
    project_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None  # PMStatus
    capacity_hours: Optional[float] = None
    planned_hours: Optional[float] = None
    goal: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class PMEpic:
    """Unified epic representation (large work items spanning multiple sprints)"""
    id: Optional[str] = None
    name: str = ""
    description: Optional[str] = None
    project_id: Optional[str] = None
    status: Optional[str] = None  # PMStatus
    priority: Optional[str] = None  # PMPriority
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    owner_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class PMComponent:
    """Unified component/module representation (technical components)"""
    id: Optional[str] = None
    name: str = ""
    description: Optional[str] = None
    project_id: Optional[str] = None
    lead_id: Optional[str] = None  # Component owner/lead
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class PMLabel:
    """Unified label/tag representation"""
    id: Optional[str] = None
    name: str = ""
    color: Optional[str] = None  # Hex color code (e.g., "#FF5733")
    description: Optional[str] = None
    project_id: Optional[str] = None  # Project-specific or global
    created_at: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class PMStatusTransition:
    """Represents a valid status transition"""
    from_status: str
    to_status: str
    name: Optional[str] = None  # User-friendly transition name
    requires_fields: Optional[List[str]] = None  # Fields required for transition
    conditions: Optional[Dict[str, Any]] = None  # Conditions that must be met


@dataclass
class PMWorkflow:
    """Represents a workflow/status board"""
    id: Optional[str] = None
    name: str = ""
    entity_type: str  # "task", "epic", "project", etc.
    project_id: Optional[str] = None
    statuses: List[str] = None  # Ordered list of statuses
    transitions: List[PMStatusTransition] = None  # Valid transitions
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize default values for lists"""
        if self.statuses is None:
            self.statuses = []
        if self.transitions is None:
            self.transitions = []


@dataclass
class PMProviderConfig:
    """Configuration for a PM provider connection"""
    provider_type: str  # "openproject", "jira", "clickup", etc.
    base_url: str
    api_key: Optional[str] = None
    api_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    organization_id: Optional[str] = None  # ClickUp space
    project_key: Optional[str] = None  # JIRA project key
    workspace_id: Optional[str] = None  # OpenProject
    additional_config: Optional[Dict[str, Any]] = None
