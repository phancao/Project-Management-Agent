"""
Base PM Provider interface

Defines the common interface that all PM providers must implement.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import date
from .models import (
    PMUser, PMProject, PMTask, PMSprint,
    PMProviderConfig, PMStatus, PMPriority
)


class BasePMProvider(ABC):
    """
    Abstract base class for all PM providers
    
    All PM providers (OpenProject, JIRA, ClickUp, etc.) must implement
    this interface to ensure consistent behavior across the system.
    """
    
    def __init__(self, config: PMProviderConfig):
        """Initialize provider with configuration"""
        self.config = config
    
    # ==================== Project Operations ====================
    
    @abstractmethod
    async def list_projects(self) -> List[PMProject]:
        """List all projects"""
        pass
    
    @abstractmethod
    async def get_project(self, project_id: str) -> Optional[PMProject]:
        """Get a single project by ID"""
        pass
    
    @abstractmethod
    async def create_project(self, project: PMProject) -> PMProject:
        """Create a new project"""
        pass
    
    @abstractmethod
    async def update_project(self, project_id: str, updates: Dict[str, Any]) -> PMProject:
        """Update an existing project"""
        pass
    
    @abstractmethod
    async def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        pass
    
    # ==================== Task Operations ====================
    
    @abstractmethod
    async def list_tasks(self, project_id: Optional[str] = None) -> List[PMTask]:
        """List all tasks, optionally filtered by project"""
        pass
    
    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[PMTask]:
        """Get a single task by ID"""
        pass
    
    @abstractmethod
    async def create_task(self, task: PMTask) -> PMTask:
        """Create a new task"""
        pass
    
    @abstractmethod
    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> PMTask:
        """Update an existing task"""
        pass
    
    @abstractmethod
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        pass
    
    # ==================== Sprint Operations ====================
    
    @abstractmethod
    async def list_sprints(self, project_id: Optional[str] = None) -> List[PMSprint]:
        """List all sprints, optionally filtered by project"""
        pass
    
    @abstractmethod
    async def get_sprint(self, sprint_id: str) -> Optional[PMSprint]:
        """Get a single sprint by ID"""
        pass
    
    @abstractmethod
    async def create_sprint(self, sprint: PMSprint) -> PMSprint:
        """Create a new sprint"""
        pass
    
    @abstractmethod
    async def update_sprint(self, sprint_id: str, updates: Dict[str, Any]) -> PMSprint:
        """Update an existing sprint"""
        pass
    
    @abstractmethod
    async def delete_sprint(self, sprint_id: str) -> bool:
        """Delete a sprint"""
        pass
    
    # ==================== User/Member Operations ====================
    
    @abstractmethod
    async def list_users(self, project_id: Optional[str] = None) -> List[PMUser]:
        """List all users/members, optionally filtered by project"""
        pass
    
    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[PMUser]:
        """Get a single user by ID"""
        pass
    
    # ==================== Health Check ====================
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider connection is healthy"""
        pass
    
    # ==================== Optional Advanced Features ====================
    
    async def bulk_create_tasks(self, tasks: List[PMTask]) -> List[PMTask]:
        """
        Bulk create tasks (optional, can be implemented for performance)
        Default implementation falls back to sequential create_task calls
        """
        results = []
        for task in tasks:
            try:
                created = await self.create_task(task)
                results.append(created)
            except Exception as e:
                # Log error and continue with remaining tasks
                print(f"Failed to create task {task.title}: {e}")
        return results
    
    async def search_tasks(self, query: str, project_id: Optional[str] = None) -> List[PMTask]:
        """
        Search tasks by query string (optional)
        Default implementation filters list_tasks
        """
        all_tasks = await self.list_tasks(project_id)
        query_lower = query.lower()
        return [
            task for task in all_tasks
            if query_lower in (task.title or "").lower()
            or query_lower in (task.description or "").lower()
        ]
    
    async def get_task_dependencies(self, task_id: str) -> List[str]:
        """
        Get task dependencies (optional)
        Returns list of task IDs that this task depends on
        """
        # Default implementation returns empty list
        return []
    
    async def sync_task_to_sprint(self, task_id: str, sprint_id: str) -> bool:
        """
        Assign a task to a sprint (optional)
        Returns True if successful
        """
        # Default implementation could update task with sprint_id
        await self.update_task(task_id, {"sprint_id": sprint_id})
        return True
