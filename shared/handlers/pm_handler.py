"""
Shared PM Handler base class.

Provides common PM operations that can be used by both PM Agent
and Meeting Notes Agent (when creating tasks from meetings).
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional

from shared.handlers.base import BaseHandler, HandlerContext, HandlerResult
from pm_providers.models import PMTask, PMProject, PMSprint, PMUser


class BasePMHandler(BaseHandler[Dict[str, Any]]):
    """
    Base handler for PM operations.
    
    Provides common methods for task creation, assignment, etc.
    that can be shared between agents.
    """
    
    @abstractmethod
    async def get_pm_provider(self, provider_id: str):
        """
        Get a PM provider instance by ID.
        
        Override this to provide the actual provider resolution logic.
        """
        pass
    
    async def create_task(
        self,
        context: HandlerContext,
        project_id: str,
        task_data: Dict[str, Any],
    ) -> HandlerResult[PMTask]:
        """
        Create a task in the PM system.
        
        Args:
            context: Handler context
            project_id: Target project ID (format: provider_id:project_key)
            task_data: Task details (title, description, etc.)
            
        Returns:
            HandlerResult with created task
        """
        try:
            provider_id, project_key = self._parse_project_id(project_id)
            provider = await self.get_pm_provider(provider_id)
            
            if not provider:
                return HandlerResult.failure(f"Provider not found: {provider_id}")
            
            task = await provider.create_task(project_key, task_data)
            return HandlerResult.success(task, message=f"Created task: {task.title}")
            
        except Exception as e:
            return HandlerResult.failure(f"Failed to create task: {str(e)}")
    
    async def create_tasks_bulk(
        self,
        context: HandlerContext,
        project_id: str,
        tasks_data: List[Dict[str, Any]],
    ) -> HandlerResult[List[PMTask]]:
        """
        Create multiple tasks at once.
        
        Args:
            context: Handler context
            project_id: Target project ID
            tasks_data: List of task details
            
        Returns:
            HandlerResult with list of created tasks
        """
        created_tasks = []
        errors = []
        
        for task_data in tasks_data:
            result = await self.create_task(context, project_id, task_data)
            if result.is_success and result.data:
                created_tasks.append(result.data)
            else:
                errors.append(result.message or "Unknown error")
        
        if errors and not created_tasks:
            return HandlerResult.failure(
                f"Failed to create all tasks",
                errors=errors,
            )
        elif errors:
            return HandlerResult.partial(
                created_tasks,
                warnings=errors,
                message=f"Created {len(created_tasks)} of {len(tasks_data)} tasks",
            )
        else:
            return HandlerResult.success(
                created_tasks,
                message=f"Created {len(created_tasks)} tasks",
            )
    
    async def assign_task(
        self,
        context: HandlerContext,
        task_id: str,
        assignee_id: str,
    ) -> HandlerResult[PMTask]:
        """
        Assign a task to a user.
        
        Args:
            context: Handler context
            task_id: Task ID to assign
            assignee_id: User ID to assign to
            
        Returns:
            HandlerResult with updated task
        """
        try:
            provider_id, task_key = self._parse_task_id(task_id)
            provider = await self.get_pm_provider(provider_id)
            
            if not provider:
                return HandlerResult.failure(f"Provider not found: {provider_id}")
            
            task = await provider.assign_task(task_key, assignee_id)
            return HandlerResult.success(task, message=f"Assigned task to {assignee_id}")
            
        except Exception as e:
            return HandlerResult.failure(f"Failed to assign task: {str(e)}")
    
    async def list_users(
        self,
        context: HandlerContext,
        project_id: str,
    ) -> HandlerResult[List[PMUser]]:
        """
        List users in a project.
        
        Args:
            context: Handler context
            project_id: Project ID
            
        Returns:
            HandlerResult with list of users
        """
        try:
            provider_id, project_key = self._parse_project_id(project_id)
            provider = await self.get_pm_provider(provider_id)
            
            if not provider:
                return HandlerResult.failure(f"Provider not found: {provider_id}")
            
            users = await provider.list_users(project_key)
            return HandlerResult.success(users, message=f"Found {len(users)} users")
            
        except Exception as e:
            return HandlerResult.failure(f"Failed to list users: {str(e)}")
    
    def _parse_project_id(self, project_id: str) -> tuple[str, str]:
        """Parse composite project ID into provider_id and project_key"""
        if ":" in project_id:
            parts = project_id.split(":", 1)
            return parts[0], parts[1]
        # Assume single provider
        return "default", project_id
    
    def _parse_task_id(self, task_id: str) -> tuple[str, str]:
        """Parse composite task ID into provider_id and task_key"""
        if ":" in task_id:
            parts = task_id.split(":", 1)
            return parts[0], parts[1]
        return "default", task_id
