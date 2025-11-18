# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Task Status Resolver - Middle Layer for Provider-Specific Status Logic

This module provides a unified interface for determining task completion status,
burndown eligibility, and other status-related queries across different PM providers.

Each provider has different ways to mark tasks as "done":
- JIRA: Uses "resolution" field - if resolution exists, task is done
- OpenProject: Uses status.is_closed or status name "Done"/"Closed" or percentage_complete = 100
- Mock: Uses status field matching "done", "closed", "completed"
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from src.pm_providers.models import PMTask


class TaskStatusResolver(ABC):
    """
    Abstract base class for resolving task status across different providers.
    
    Each provider implements this interface to handle provider-specific logic
    for determining completion, burndown eligibility, etc.
    """
    
    @abstractmethod
    def is_completed(self, task: PMTask) -> bool:
        """
        Check if a task is completed (done/closed/resolved).
        
        Args:
            task: PMTask object
            
        Returns:
            True if task is completed, False otherwise
        """
        pass
    
    @abstractmethod
    def is_burndowned(self, task: PMTask) -> bool:
        """
        Check if a task is "burndowned" (counts toward burndown).
        
        This may differ from is_completed() - for example, in some systems,
        a task might be "done" but not yet "burndowned" until it's verified.
        
        By default, this should return the same as is_completed(), but can be
        overridden for provider-specific logic.
        
        Args:
            task: PMTask object
            
        Returns:
            True if task is burndowned, False otherwise
        """
        pass
    
    @abstractmethod
    def get_completion_date(self, task: PMTask) -> Optional[datetime]:
        """
        Get the date when the task was completed.
        
        Args:
            task: PMTask object
            
        Returns:
            Completion datetime, or None if not completed
        """
        pass
    
    @abstractmethod
    def get_start_date(self, task: PMTask) -> Optional[datetime]:
        """
        Get the date when the task started (for cycle time calculation).
        
        Args:
            task: PMTask object
            
        Returns:
            Start datetime, or None if not started
        """
        pass
    
    @abstractmethod
    def get_status_category(self, task: PMTask) -> str:
        """
        Categorize task status into: "todo", "in_progress", "done", "blocked".
        
        Args:
            task: PMTask object
            
        Returns:
            Status category string
        """
        pass
    
    @abstractmethod
    def extract_story_points(self, task: PMTask) -> float:
        """
        Extract story points from task.
        
        Different providers store story points differently:
        - JIRA: In raw_data["fields"]["customfield_10016"] or similar
        - OpenProject: In raw_data["storyPoints"] or estimated_hours / 8
        - Mock: In raw_data["storyPoints"] or estimated_hours / 8
        
        Args:
            task: PMTask object
            
        Returns:
            Story points value (0 if not available)
        """
        pass
    
    @abstractmethod
    def get_status_history(self, task: PMTask) -> List[Dict[str, Any]]:
        """
        Get status change history for the task.
        
        This is used for CFD charts to track status changes over time.
        
        Args:
            task: PMTask object
            
        Returns:
            List of status changes with "date" and "status" keys
        """
        pass
    
    def get_task_type(self, task: PMTask) -> str:
        """
        Get task type (Story, Bug, Task, Epic, etc.).
        
        Args:
            task: PMTask object
            
        Returns:
            Task type string
        """
        if task.raw_data:
            # Try to get from raw_data
            if isinstance(task.raw_data, dict):
                # JIRA: fields.issuetype.name
                if "fields" in task.raw_data:
                    issue_type = task.raw_data["fields"].get("issuetype", {})
                    if isinstance(issue_type, dict):
                        return issue_type.get("name", "Task")
                # OpenProject: type or _embedded.type.name
                if "type" in task.raw_data:
                    type_obj = task.raw_data["type"]
                    if isinstance(type_obj, dict):
                        return type_obj.get("name", "Task")
                if "_embedded" in task.raw_data:
                    type_obj = task.raw_data["_embedded"].get("type", {})
                    if isinstance(type_obj, dict):
                        return type_obj.get("name", "Task")
        return "Task"


class JIRATaskStatusResolver(TaskStatusResolver):
    """
    JIRA-specific task status resolver.
    
    JIRA determines completion by:
    - Resolution field: If resolution exists, task is done
    - Resolution date: When task was completed
    - Status: Can also check status name, but resolution is primary indicator
    """
    
    def is_completed(self, task: PMTask) -> bool:
        """JIRA: Task is completed if resolution field exists"""
        if not task.raw_data:
            # Fallback to status if no raw_data
            status_lower = (task.status or "").lower()
            return any(keyword in status_lower for keyword in ["done", "closed", "completed", "resolved"])
        
        fields = task.raw_data.get("fields", {})
        resolution = fields.get("resolution")
        
        # If resolution exists, task is done
        if resolution is not None:
            return True
        
        # Fallback: Check status name
        status_obj = fields.get("status", {})
        status_name = (status_obj.get("name", "") or "").lower()
        return any(keyword in status_name for keyword in ["done", "closed", "completed", "resolved"])
    
    def is_burndowned(self, task: PMTask) -> bool:
        """
        JIRA: Task is burndowned if it has a resolution.
        For burndown purposes, we use the same logic as completion.
        """
        return self.is_completed(task)
    
    def get_completion_date(self, task: PMTask) -> Optional[datetime]:
        """JIRA: Get resolutiondate from fields"""
        if task.completed_at:
            return task.completed_at
        
        if task.raw_data:
            fields = task.raw_data.get("fields", {})
            resolution_date_str = fields.get("resolutiondate")
            if resolution_date_str:
                try:
                    return datetime.fromisoformat(resolution_date_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass
        
        return None
    
    def get_start_date(self, task: PMTask) -> Optional[datetime]:
        """JIRA: Get startdate or created_at"""
        if task.start_date:
            return datetime.combine(task.start_date, datetime.min.time())
        
        if task.raw_data:
            fields = task.raw_data.get("fields", {})
            start_date_str = fields.get("startdate")
            if start_date_str:
                try:
                    return datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass
        
        # Fallback to created_at
        if task.created_at:
            return task.created_at
        
        return None
    
    def get_status_category(self, task: PMTask) -> str:
        """Categorize JIRA status"""
        status_lower = (task.status or "").lower()
        
        if any(keyword in status_lower for keyword in ["done", "closed", "completed", "resolved"]):
            return "done"
        elif "block" in status_lower or "hold" in status_lower:
            return "blocked"
        elif "progress" in status_lower or "doing" in status_lower:
            return "in_progress"
        else:
            return "todo"
    
    def extract_story_points(self, task: PMTask) -> float:
        """Extract story points from JIRA task"""
        if task.raw_data:
            fields = task.raw_data.get("fields", {})
            
            # JIRA story points field (customfield_10016 is common, but varies)
            # Try common field names
            story_points = (
                fields.get("customfield_10016") or  # Common JIRA field
                fields.get("storyPoints") or
                fields.get("story_points")
            )
            
            if story_points is not None:
                try:
                    return float(story_points)
                except (ValueError, TypeError):
                    pass
        
        # Fallback: Convert estimated hours to story points (8 hours = 1 point)
        if task.estimated_hours:
            return task.estimated_hours / 8.0
        
        return 0.0
    
    def get_status_history(self, task: PMTask) -> List[Dict[str, Any]]:
        """
        Get status history from JIRA changelog.
        
        JIRA stores status changes in changelog.histories.
        """
        history = []
        
        if not task.raw_data:
            # Fallback: Use created_at and current status
            if task.created_at:
                history.append({
                    "date": task.created_at.isoformat(),
                    "status": task.status or "To Do"
                })
            return history
        
        # Get changelog
        changelog = task.raw_data.get("changelog", {})
        histories = changelog.get("histories", [])
        
        # Extract status changes from changelog
        for change in histories:
            created = change.get("created")
            items = change.get("items", [])
            
            for item in items:
                if item.get("field") == "status":
                    from_status = item.get("fromString", "To Do")
                    to_status = item.get("toString", "To Do")
                    
                    if created:
                        history.append({
                            "date": created,
                            "status": to_status
                        })
        
        # If no history found, use created_at and current status
        if not history:
            if task.created_at:
                history.append({
                    "date": task.created_at.isoformat(),
                    "status": task.status or "To Do"
                })
            if task.completed_at:
                history.append({
                    "date": task.completed_at.isoformat(),
                    "status": task.status or "Done"
                })
        
        return history


class OpenProjectTaskStatusResolver(TaskStatusResolver):
    """
    OpenProject-specific task status resolver.
    
    OpenProject determines completion by:
    - Status.is_closed: Boolean flag indicating if status is closed
    - Status name: "Done", "Closed", "Completed"
    - Percentage complete: 100% means done
    """
    
    def is_completed(self, task: PMTask) -> bool:
        """OpenProject: Task is completed if status is closed or percentage is 100%"""
        if task.raw_data:
            # Check status.is_closed flag
            status_obj = task.raw_data.get("_embedded", {}).get("status", {})
            if isinstance(status_obj, dict):
                is_closed = status_obj.get("isClosed", False)
                if is_closed:
                    return True
            
            # Check status name
            status_name = status_obj.get("name", "") if isinstance(status_obj, dict) else ""
            if not status_name:
                # Try direct status field
                status_obj = task.raw_data.get("status", {})
                status_name = status_obj.get("name", "") if isinstance(status_obj, dict) else ""
            
            status_lower = status_name.lower()
            if any(keyword in status_lower for keyword in ["done", "closed", "completed"]):
                return True
            
            # Check percentage complete
            percentage_complete = task.raw_data.get("percentageComplete") or task.raw_data.get("percentage_complete")
            if percentage_complete is not None:
                try:
                    if float(percentage_complete) >= 100.0:
                        return True
                except (ValueError, TypeError):
                    pass
        
        # Fallback: Check unified status field
        status_lower = (task.status or "").lower()
        return any(keyword in status_lower for keyword in ["done", "closed", "completed"])
    
    def is_burndowned(self, task: PMTask) -> bool:
        """
        OpenProject: Task is burndowned if status is closed or percentage is 100%.
        Same as completion for OpenProject.
        """
        return self.is_completed(task)
    
    def get_completion_date(self, task: PMTask) -> Optional[datetime]:
        """OpenProject: Get completion date"""
        if task.completed_at:
            return task.completed_at
        
        if task.raw_data:
            # OpenProject might store completion date in different fields
            completion_date_str = (
                task.raw_data.get("date") or
                task.raw_data.get("completionDate") or
                task.raw_data.get("completion_date") or
                task.raw_data.get("updatedAt") or  # Use updatedAt as fallback
                task.raw_data.get("updated_at")
            )
            if completion_date_str:
                try:
                    return datetime.fromisoformat(completion_date_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass
            
            # If task is 100% complete but no completion date, use updatedAt or created_at
            percentage_complete = task.raw_data.get("percentageComplete") or task.raw_data.get("percentage_complete")
            if percentage_complete is not None:
                try:
                    if float(percentage_complete) >= 100.0:
                        # Task is 100% complete, use updatedAt or created_at as completion date
                        updated_at_str = task.raw_data.get("updatedAt") or task.raw_data.get("updated_at")
                        if updated_at_str:
                            try:
                                return datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                            except (ValueError, AttributeError):
                                pass
                        # Fallback to created_at if available
                        if task.created_at:
                            return task.created_at
                except (ValueError, TypeError):
                    pass
        
        return None
    
    def get_start_date(self, task: PMTask) -> Optional[datetime]:
        """OpenProject: Get start date"""
        if task.start_date:
            return datetime.combine(task.start_date, datetime.min.time())
        
        if task.raw_data:
            start_date_str = task.raw_data.get("startDate") or task.raw_data.get("start_date")
            if start_date_str:
                try:
                    return datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass
        
        # Fallback to created_at
        if task.created_at:
            return task.created_at
        
        return None
    
    def get_status_category(self, task: PMTask) -> str:
        """Categorize OpenProject status"""
        if task.raw_data:
            status_obj = task.raw_data.get("_embedded", {}).get("status", {})
            if isinstance(status_obj, dict):
                is_closed = status_obj.get("isClosed", False)
                if is_closed:
                    return "done"
                
                status_name = status_obj.get("name", "")
                status_lower = status_name.lower()
                if any(keyword in status_lower for keyword in ["done", "closed", "completed"]):
                    return "done"
                elif "progress" in status_lower or "doing" in status_lower:
                    return "in_progress"
        
        # Fallback to unified status
        status_lower = (task.status or "").lower()
        if any(keyword in status_lower for keyword in ["done", "closed", "completed"]):
            return "done"
        elif "progress" in status_lower or "doing" in status_lower:
            return "in_progress"
        elif "block" in status_lower:
            return "blocked"
        else:
            return "todo"
    
    def extract_story_points(self, task: PMTask) -> float:
        """Extract story points from OpenProject task"""
        if task.raw_data:
            # OpenProject stores story points in storyPoints field
            story_points = (
                task.raw_data.get("storyPoints") or
                task.raw_data.get("story_points")
            )
            
            if story_points is not None:
                try:
                    return float(story_points)
                except (ValueError, TypeError):
                    pass
        
        # Fallback: Convert estimated hours to story points (8 hours = 1 point)
        if task.estimated_hours:
            return task.estimated_hours / 8.0
        
        return 0.0
    
    def get_status_history(self, task: PMTask) -> List[Dict[str, Any]]:
        """
        Get status history from OpenProject.
        
        OpenProject may store status history in _embedded.activities or similar.
        For now, we'll use created_at and current status.
        """
        history = []
        
        if task.created_at:
            history.append({
                "date": task.created_at.isoformat(),
                "status": task.status or "To Do"
            })
        
        if task.completed_at and self.is_completed(task):
            history.append({
                "date": task.completed_at.isoformat(),
                "status": task.status or "Done"
            })
        
        return history


class MockTaskStatusResolver(TaskStatusResolver):
    """
    Mock provider task status resolver.
    
    Mock provider uses simple status field matching.
    """
    
    def is_completed(self, task: PMTask) -> bool:
        """Mock: Check status field"""
        status_lower = (task.status or "").lower()
        return any(keyword in status_lower for keyword in ["done", "closed", "completed"])
    
    def is_burndowned(self, task: PMTask) -> bool:
        """Mock: Same as completion"""
        return self.is_completed(task)
    
    def get_completion_date(self, task: PMTask) -> Optional[datetime]:
        """Mock: Get completed_at"""
        return task.completed_at
    
    def get_start_date(self, task: PMTask) -> Optional[datetime]:
        """Mock: Get start_date or created_at"""
        if task.start_date:
            return datetime.combine(task.start_date, datetime.min.time())
        return task.created_at
    
    def get_status_category(self, task: PMTask) -> str:
        """Categorize Mock status"""
        status_lower = (task.status or "").lower()
        
        if any(keyword in status_lower for keyword in ["done", "closed", "completed"]):
            return "done"
        elif "block" in status_lower:
            return "blocked"
        elif "progress" in status_lower:
            return "in_progress"
        else:
            return "todo"
    
    def extract_story_points(self, task: PMTask) -> float:
        """Extract story points from Mock task"""
        if task.raw_data:
            story_points = task.raw_data.get("storyPoints") or task.raw_data.get("story_points")
            if story_points is not None:
                try:
                    return float(story_points)
                except (ValueError, TypeError):
                    pass
        
        # Fallback: Convert estimated hours to story points
        if task.estimated_hours:
            return task.estimated_hours / 8.0
        
        return 0.0
    
    def get_status_history(self, task: PMTask) -> List[Dict[str, Any]]:
        """Mock: Simple status history"""
        history = []
        
        if task.created_at:
            history.append({
                "date": task.created_at.isoformat(),
                "status": task.status or "To Do"
            })
        
        if task.completed_at:
            history.append({
                "date": task.completed_at.isoformat(),
                "status": task.status or "Done"
            })
        
        return history


def create_task_status_resolver(provider_type: str) -> TaskStatusResolver:
    """
    Factory function to create appropriate task status resolver for provider.
    
    Args:
        provider_type: Provider type string (e.g., "jira", "openproject", "mock")
        
    Returns:
        TaskStatusResolver instance
    """
    provider_type_lower = provider_type.lower()
    
    if "jira" in provider_type_lower:
        return JIRATaskStatusResolver()
    elif "openproject" in provider_type_lower:
        return OpenProjectTaskStatusResolver()
    elif "mock" in provider_type_lower:
        return MockTaskStatusResolver()
    else:
        # Default to Mock resolver for unknown providers
        return MockTaskStatusResolver()

