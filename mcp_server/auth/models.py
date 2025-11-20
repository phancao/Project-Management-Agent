"""
Authentication Models

Defines data models for users, roles, permissions, and tokens.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class Role(str, Enum):
    """User roles with hierarchical permissions."""
    ADMIN = "admin"           # Full access to all operations
    DEVELOPER = "developer"   # Read/write access to tasks, projects
    VIEWER = "viewer"         # Read-only access
    QC = "qc"                # QC-specific operations (defects, testing)
    PM = "pm"                # Project manager operations
    AGENT = "agent"          # AI agent access (configurable)


class Permission(str, Enum):
    """Granular permissions for operations."""
    # Project permissions
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    PROJECT_DELETE = "project:delete"
    
    # Task permissions
    TASK_READ = "task:read"
    TASK_WRITE = "task:write"
    TASK_DELETE = "task:delete"
    TASK_ASSIGN = "task:assign"
    
    # Sprint permissions
    SPRINT_READ = "sprint:read"
    SPRINT_WRITE = "sprint:write"
    SPRINT_DELETE = "sprint:delete"
    SPRINT_MANAGE = "sprint:manage"  # Start/complete sprints
    
    # Epic permissions
    EPIC_READ = "epic:read"
    EPIC_WRITE = "epic:write"
    EPIC_DELETE = "epic:delete"
    
    # User permissions
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    
    # Analytics permissions
    ANALYTICS_READ = "analytics:read"
    
    # Admin permissions
    ADMIN_ALL = "admin:all"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[Role, list[Permission]] = {
    Role.ADMIN: [Permission.ADMIN_ALL],  # Admin has all permissions
    
    Role.DEVELOPER: [
        Permission.PROJECT_READ,
        Permission.TASK_READ,
        Permission.TASK_WRITE,
        Permission.TASK_ASSIGN,
        Permission.SPRINT_READ,
        Permission.EPIC_READ,
        Permission.USER_READ,
        Permission.ANALYTICS_READ,
    ],
    
    Role.VIEWER: [
        Permission.PROJECT_READ,
        Permission.TASK_READ,
        Permission.SPRINT_READ,
        Permission.EPIC_READ,
        Permission.USER_READ,
        Permission.ANALYTICS_READ,
    ],
    
    Role.QC: [
        Permission.PROJECT_READ,
        Permission.TASK_READ,
        Permission.TASK_WRITE,  # Create defects
        Permission.SPRINT_READ,
        Permission.USER_READ,
        Permission.ANALYTICS_READ,
    ],
    
    Role.PM: [
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.TASK_READ,
        Permission.TASK_WRITE,
        Permission.TASK_DELETE,
        Permission.TASK_ASSIGN,
        Permission.SPRINT_READ,
        Permission.SPRINT_WRITE,
        Permission.SPRINT_MANAGE,
        Permission.EPIC_READ,
        Permission.EPIC_WRITE,
        Permission.USER_READ,
        Permission.ANALYTICS_READ,
    ],
    
    Role.AGENT: [
        # Configurable per agent, default to developer permissions
        Permission.PROJECT_READ,
        Permission.TASK_READ,
        Permission.TASK_WRITE,
        Permission.SPRINT_READ,
        Permission.EPIC_READ,
        Permission.USER_READ,
        Permission.ANALYTICS_READ,
    ],
}


@dataclass
class User:
    """User model with authentication and authorization info."""
    id: str
    username: str
    email: str
    role: Role
    permissions: list[Permission] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize permissions based on role if not provided."""
        if not self.permissions:
            self.permissions = ROLE_PERMISSIONS.get(self.role, [])
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        # Admin has all permissions
        if Permission.ADMIN_ALL in self.permissions:
            return True
        
        return permission in self.permissions
    
    def has_any_permission(self, permissions: list[Permission]) -> bool:
        """Check if user has any of the specified permissions."""
        if Permission.ADMIN_ALL in self.permissions:
            return True
        
        return any(p in self.permissions for p in permissions)
    
    def has_all_permissions(self, permissions: list[Permission]) -> bool:
        """Check if user has all of the specified permissions."""
        if Permission.ADMIN_ALL in self.permissions:
            return True
        
        return all(p in self.permissions for p in permissions)
    
    def add_permission(self, permission: Permission) -> None:
        """Add a permission to the user."""
        if permission not in self.permissions:
            self.permissions.append(permission)
    
    def remove_permission(self, permission: Permission) -> None:
        """Remove a permission from the user."""
        if permission in self.permissions:
            self.permissions.remove(permission)


@dataclass
class Token:
    """Authentication token model."""
    token: str
    user_id: str
    expires_at: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_revoked: bool = False
    metadata: dict = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        token: str,
        user_id: str,
        expires_in_hours: int = 24
    ) -> "Token":
        """Create a new token with expiration."""
        return cls(
            token=token,
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours)
        )
    
    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)."""
        return (
            not self.is_revoked
            and datetime.utcnow() < self.expires_at
        )
    
    def revoke(self) -> None:
        """Revoke the token."""
        self.is_revoked = True


# Tool to permission mapping
TOOL_PERMISSIONS: dict[str, list[Permission]] = {
    # Project tools
    "list_projects": [Permission.PROJECT_READ],
    "get_project": [Permission.PROJECT_READ],
    "create_project": [Permission.PROJECT_WRITE],
    "update_project": [Permission.PROJECT_WRITE],
    "delete_project": [Permission.PROJECT_DELETE],
    "search_projects": [Permission.PROJECT_READ],
    
    # Task tools
    "list_my_tasks": [Permission.TASK_READ],
    "list_tasks": [Permission.TASK_READ],
    "get_task": [Permission.TASK_READ],
    "create_task": [Permission.TASK_WRITE],
    "update_task": [Permission.TASK_WRITE],
    "delete_task": [Permission.TASK_DELETE],
    "assign_task": [Permission.TASK_ASSIGN],
    "update_task_status": [Permission.TASK_WRITE],
    "search_tasks": [Permission.TASK_READ],
    "bulk_update_tasks": [Permission.TASK_WRITE],
    
    # Sprint tools
    "list_sprints": [Permission.SPRINT_READ],
    "get_sprint": [Permission.SPRINT_READ],
    "create_sprint": [Permission.SPRINT_WRITE],
    "update_sprint": [Permission.SPRINT_WRITE],
    "delete_sprint": [Permission.SPRINT_DELETE],
    "start_sprint": [Permission.SPRINT_MANAGE],
    "complete_sprint": [Permission.SPRINT_MANAGE],
    "add_task_to_sprint": [Permission.SPRINT_WRITE, Permission.TASK_WRITE],
    "remove_task_from_sprint": [Permission.SPRINT_WRITE, Permission.TASK_WRITE],
    "get_sprint_tasks": [Permission.SPRINT_READ],
    
    # Epic tools
    "list_epics": [Permission.EPIC_READ],
    "get_epic": [Permission.EPIC_READ],
    "create_epic": [Permission.EPIC_WRITE],
    "update_epic": [Permission.EPIC_WRITE],
    "delete_epic": [Permission.EPIC_DELETE],
    "link_task_to_epic": [Permission.EPIC_WRITE, Permission.TASK_WRITE],
    "unlink_task_from_epic": [Permission.EPIC_WRITE, Permission.TASK_WRITE],
    "get_epic_progress": [Permission.EPIC_READ],
    
    # User tools
    "list_users": [Permission.USER_READ],
    "get_current_user": [Permission.USER_READ],
    "get_user": [Permission.USER_READ],
    "search_users": [Permission.USER_READ],
    "get_user_workload": [Permission.USER_READ],
    
    # Analytics tools
    "burndown_chart": [Permission.ANALYTICS_READ],
    "velocity_chart": [Permission.ANALYTICS_READ],
    "sprint_report": [Permission.ANALYTICS_READ],
    "project_health": [Permission.ANALYTICS_READ],
    "task_distribution": [Permission.ANALYTICS_READ],
    "team_performance": [Permission.ANALYTICS_READ],
    "gantt_chart": [Permission.ANALYTICS_READ],
    "epic_report": [Permission.ANALYTICS_READ],
    "resource_utilization": [Permission.ANALYTICS_READ],
    "time_tracking_report": [Permission.ANALYTICS_READ],
    
    # Task interaction tools
    "add_task_comment": [Permission.TASK_WRITE],
    "get_task_comments": [Permission.TASK_READ],
    "add_task_watcher": [Permission.TASK_WRITE],
    "link_related_tasks": [Permission.TASK_WRITE],
}

