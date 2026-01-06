"""
Base PM Provider interface

Defines the common interface that all PM providers must implement.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncIterator
from datetime import date
from .models import (
    PMUser, PMProject, PMTask, PMSprint, PMEpic, PMComponent, PMLabel,
    PMProviderConfig, PMStatus, PMPriority, PMStatusTransition
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
    async def list_projects(self, user_id: Optional[str] = None) -> AsyncIterator[PMProject]:
        """
        List all projects.
        Yields projects one by one.
        """
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
    async def list_tasks(
        self, 
        project_id: Optional[str] = None, 
        assignee_id: Optional[str] = None,
        sprint_id: Optional[str] = None
    ) -> AsyncIterator[PMTask]:
        """
        List all tasks, optionally filtered by project, assignee, and/or sprint.
        Yields tasks one by one to handle large datasets.
        """
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
    async def list_sprints(
        self, project_id: Optional[str] = None, state: Optional[str] = None
    ) -> AsyncIterator[PMSprint]:
        """
        List all sprints, optionally filtered by project.
        Yields sprints one by one.
        """
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
    async def list_users(self, project_id: Optional[str] = None) -> AsyncIterator[PMUser]:
        """
        List all users/members, optionally filtered by project.
        Yields users one by one.
        """
        pass
    
    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[PMUser]:
        """Get a single user by ID"""
        pass
    
    async def get_current_user(self) -> Optional[PMUser]:
        """
        Get the current user associated with the API key/token
        This should be overridden by providers that support it
        
        Returns:
            Current user or None if not supported
        """
        return None
        
    @abstractmethod
    async def get_time_entries(
        self,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Get time entries, optionally filtered.
        Yields entries one by one.
        """
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
    
    # ==================== Epic Operations ====================
    
    @abstractmethod
    async def list_epics(self, project_id: Optional[str] = None) -> AsyncIterator[PMEpic]:
        """
        List all epics, optionally filtered by project.
        Yields epics one by one.
        """
        pass
    
    @abstractmethod
    async def get_epic(self, epic_id: str) -> Optional[PMEpic]:
        """Get a single epic by ID"""
        pass
    
    @abstractmethod
    async def create_epic(self, epic: PMEpic) -> PMEpic:
        """Create a new epic"""
        pass
    
    @abstractmethod
    async def update_epic(self, epic_id: str, updates: Dict[str, Any]) -> PMEpic:
        """Update an existing epic"""
        pass
    
    @abstractmethod
    async def delete_epic(self, epic_id: str) -> bool:
        """Delete an epic"""
        pass
    
    async def get_epic_tasks(self, epic_id: str) -> List[PMTask]:
        """
        Get all tasks associated with an epic (optional)
        Default implementation filters tasks by epic_id
        """
        all_tasks = await self.list_tasks()
        return [t for t in all_tasks if t.epic_id == epic_id]
    
    async def assign_task_to_epic(self, task_id: str, epic_id: str) -> PMTask:
        """
        Assign a task to an epic.
        
        This sets the epic_id field on the task, creating a link between
        the task and the epic.
        
        Args:
            task_id: ID of the task to assign
            epic_id: ID of the epic to assign to
            
        Returns:
            Updated task with epic_id set
        """
        updates = {"epic_id": epic_id}
        return await self.update_task(task_id, updates)
    
    async def remove_task_from_epic(self, task_id: str) -> PMTask:
        """
        Remove a task from its epic.
        
        This clears the epic_id field on the task.
        
        Args:
            task_id: ID of the task to remove from epic
            
        Returns:
            Updated task with epic_id cleared
        """
        updates = {"epic_id": None}
        return await self.update_task(task_id, updates)
    
    async def assign_task_to_sprint(self, task_id: str, sprint_id: str) -> PMTask:
        """
        Assign a task to a sprint.
        
        Args:
            task_id: ID of the task to assign
            sprint_id: ID of the sprint to assign to
            
        Returns:
            Updated task with sprint_id set
        """
        updates = {"sprint_id": sprint_id}
        return await self.update_task(task_id, updates)
    
    async def move_task_to_backlog(self, task_id: str) -> PMTask:
        """
        Move a task to the backlog (remove from sprint).
        
        Args:
            task_id: ID of the task to move to backlog
            
        Returns:
            Updated task with sprint_id cleared
        """
        updates = {"sprint_id": None}
        return await self.update_task(task_id, updates)
    
    # ==================== Label Operations ====================
    
    @abstractmethod
    async def list_labels(self, project_id: Optional[str] = None) -> List[PMLabel]:
        """List all labels, optionally filtered by project"""
        pass
    
    @abstractmethod
    async def get_label(self, label_id: str) -> Optional[PMLabel]:
        """Get a single label by ID"""
        pass
    
    @abstractmethod
    async def create_label(self, label: PMLabel) -> PMLabel:
        """Create a new label"""
        pass
    
    @abstractmethod
    async def update_label(self, label_id: str, updates: Dict[str, Any]) -> PMLabel:
        """Update an existing label"""
        pass
    
    @abstractmethod
    async def delete_label(self, label_id: str) -> bool:
        """Delete a label"""
        pass
    
    async def get_label_tasks(self, label_id: str) -> List[PMTask]:
        """
        Get all tasks with a specific label (optional)
        Default implementation filters tasks by label_ids
        """
        all_tasks = await self.list_tasks()
        return [
            t for t in all_tasks
            if t.label_ids and label_id in t.label_ids
        ]
    
    # ==================== Status Operations ====================
    
    @abstractmethod
    async def list_statuses(self, entity_type: str, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of available statuses for an entity type.
        
        This is primarily used for UI/UX to create status columns in Kanban boards.
        
        Args:
            entity_type: Type of entity ("task", "epic", "project", "sprint", etc.)
            project_id: Optional project ID for project-specific statuses
            
        Returns:
            List of status objects with at least: {"id": str, "name": str, "color": Optional[str]}
        """
        pass
    
    async def get_valid_transitions(
        self,
        entity_id: str,
        entity_type: str
    ) -> List[str]:
        """
        Get valid status transitions for an entity (optional)
        
        Returns list of status names that the entity can transition to.
        If not implemented, returns all available statuses.
        
        Args:
            entity_id: ID of the entity
            entity_type: Type of entity ("task", "epic", "project", etc.)
            
        Returns:
            List of valid target status names
        """
        # Default implementation: return all statuses
        # Specific providers can override to return only valid transitions
        return await self.list_statuses(entity_type)
    
    async def transition_status(
        self,
        entity_id: str,
        entity_type: str,
        to_status: str,
        comment: Optional[str] = None
    ) -> bool:
        """
        Transition an entity to a new status (optional)
        
        Args:
            entity_id: ID of the entity
            entity_type: Type of entity ("task", "epic", "project", etc.)
            to_status: Target status
            comment: Optional comment for the transition
            
        Returns:
            True if transition successful
            
        Raises:
            ValueError: If transition is invalid
        """
        # Validate that target status exists
        valid_statuses = await self.list_statuses(entity_type)
        valid_status_names = [s.get("name") if isinstance(s, dict) else s for s in valid_statuses]
        if to_status not in valid_status_names:
            raise ValueError(
                f"Invalid status '{to_status}'. "
                f"Valid statuses: {valid_statuses}"
            )
        
        # Optionally validate transition rules
        valid_transitions = await self.get_valid_transitions(entity_id, entity_type)
        if valid_transitions and to_status not in valid_transitions:
            raise ValueError(
                f"Invalid status transition to '{to_status}'. "
                f"Valid transitions: {valid_transitions}"
            )
        
        # Perform transition
        updates = {"status": to_status}
        if comment:
            updates["comment"] = comment
        
        if entity_type == "task":
            await self.update_task(entity_id, updates)
        elif entity_type == "epic":
            await self.update_epic(entity_id, updates)
        elif entity_type == "project":
            await self.update_project(entity_id, updates)
        else:
            raise ValueError(f"Unsupported entity type: {entity_type}")
        
        return True
    
    # ==================== Priority Operations ====================
    
    async def list_priorities(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of available priorities (optional).
        
        This is primarily used for UI/UX to populate priority dropdowns/selectors.
        
        Args:
            project_id: Optional project ID for project-specific priorities
            
        Returns:
            List of priority objects with at least: {"id": str, "name": str, "color": Optional[str]}
            
        Raises:
            NotImplementedError: If not implemented by the provider
        """
        raise NotImplementedError(
            f"list_priorities not implemented for {self.__class__.__name__}"
        )