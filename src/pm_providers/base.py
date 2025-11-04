"""
Base PM Provider interface

Defines the common interface that all PM providers must implement.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import date
from .models import (
    PMUser, PMProject, PMTask, PMSprint, PMEpic, PMComponent, PMLabel,
    PMProviderConfig, PMStatus, PMPriority, PMStatusTransition, PMWorkflow
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
    async def list_tasks(self, project_id: Optional[str] = None, assignee_id: Optional[str] = None) -> List[PMTask]:
        """List all tasks, optionally filtered by project and/or assignee"""
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
    
    async def get_current_user(self) -> Optional[PMUser]:
        """
        Get the current user associated with the API key/token
        This should be overridden by providers that support it
        
        Returns:
            Current user or None if not supported
        """
        return None
    
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
    async def list_epics(self, project_id: Optional[str] = None) -> List[PMEpic]:
        """List all epics, optionally filtered by project"""
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
    
    # ==================== Component Operations ====================
    
    @abstractmethod
    async def list_components(self, project_id: Optional[str] = None) -> List[PMComponent]:
        """List all components, optionally filtered by project"""
        pass
    
    @abstractmethod
    async def get_component(self, component_id: str) -> Optional[PMComponent]:
        """Get a single component by ID"""
        pass
    
    @abstractmethod
    async def create_component(self, component: PMComponent) -> PMComponent:
        """Create a new component"""
        pass
    
    @abstractmethod
    async def update_component(self, component_id: str, updates: Dict[str, Any]) -> PMComponent:
        """Update an existing component"""
        pass
    
    @abstractmethod
    async def delete_component(self, component_id: str) -> bool:
        """Delete a component"""
        pass
    
    async def get_component_tasks(self, component_id: str) -> List[PMTask]:
        """
        Get all tasks associated with a component (optional)
        Default implementation filters tasks by component_ids
        """
        all_tasks = await self.list_tasks()
        return [
            t for t in all_tasks
            if t.component_ids and component_id in t.component_ids
        ]
    
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
    
    # ==================== Status Workflow Operations ====================
    
    @abstractmethod
    async def get_workflow(self, entity_type: str, project_id: Optional[str] = None) -> Optional[PMWorkflow]:
        """
        Get the workflow for an entity type (task, epic, project, etc.)
        
        Args:
            entity_type: Type of entity ("task", "epic", "project", etc.)
            project_id: Optional project ID for project-specific workflows
            
        Returns:
            Workflow definition or None if not found
        """
        pass
    
    @abstractmethod
    async def list_workflows(self, project_id: Optional[str] = None) -> List[PMWorkflow]:
        """List all workflows, optionally filtered by project"""
        pass
    
    async def get_valid_transitions(
        self,
        entity_id: str,
        entity_type: str
    ) -> List[PMStatusTransition]:
        """
        Get valid status transitions for an entity (optional)
        
        Args:
            entity_id: ID of the entity
            entity_type: Type of entity ("task", "epic", "project", etc.)
            
        Returns:
            List of valid transitions from current status
        """
        workflow = await self.get_workflow(entity_type)
        if not workflow:
            return []
        
        # Get current entity status
        entity = None
        if entity_type == "task":
            entity = await self.get_task(entity_id)
        elif entity_type == "epic":
            entity = await self.get_epic(entity_id)
        elif entity_type == "project":
            entity = await self.get_project(entity_id)
        else:
            return []
        
        if not entity or not entity.status:
            return []
        
        current_status = entity.status
        return [
            t for t in workflow.transitions
            if t.from_status == current_status
        ]
    
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
        # Validate transition
        valid_transitions = await self.get_valid_transitions(entity_id, entity_type)
        if not any(t.to_status == to_status for t in valid_transitions):
            raise ValueError(
                f"Invalid status transition to {to_status}. "
                f"Valid transitions: {[t.to_status for t in valid_transitions]}"
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
