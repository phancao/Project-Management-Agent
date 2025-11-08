# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
PM Provider Analytics Adapter

Fetches real data from PM providers (OpenProject, JIRA) and transforms it
for analytics calculators.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
from collections import defaultdict

from src.pm_providers.base import BasePMProvider
from src.pm_providers.models import PMTask, PMSprint, PMProject
from .base import BaseAnalyticsAdapter

logger = logging.getLogger(__name__)


class PMProviderAnalyticsAdapter(BaseAnalyticsAdapter):
    """
    Analytics adapter that fetches data from PM providers.
    """
    
    def __init__(self, provider: BasePMProvider):
        """
        Initialize adapter with a PM provider.
        
        Args:
            provider: PM provider instance (OpenProject, JIRA, etc.)
        """
        self.provider = provider
    
    async def get_burndown_data(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        scope_type: str = "story_points"
    ) -> Dict[str, Any]:
        """Fetch burndown data from PM provider"""
        logger.info(f"[PMProviderAnalyticsAdapter] Fetching burndown data: project={project_id}, sprint={sprint_id}")
        
        try:
            # Get sprint info
            if not sprint_id:
                # Get active sprint
                sprints = await self.provider.list_sprints(project_id=project_id, state="active")
                if not sprints:
                    # Fallback to any sprint
                    sprints = await self.provider.list_sprints(project_id=project_id)
                if not sprints:
                    raise ValueError(f"No sprints found for project {project_id}")
                sprint = sprints[0]
                sprint_id = sprint.id
            else:
                sprint = await self.provider.get_sprint(sprint_id)
            
            if not sprint:
                raise ValueError(f"Sprint {sprint_id} not found")
            
            # Get all tasks in the sprint
            all_tasks = await self.provider.list_tasks(project_id=project_id)
            sprint_tasks = [t for t in all_tasks if t.sprint_id == sprint_id]
            
            logger.info(f"[PMProviderAnalyticsAdapter] Found {len(sprint_tasks)} tasks in sprint {sprint_id}")
            
            # Transform tasks for burndown calculator
            tasks_data = []
            for task in sprint_tasks:
                # Extract story points from raw_data or estimated_hours
                story_points = 0
                if task.raw_data and "storyPoints" in task.raw_data:
                    story_points = task.raw_data["storyPoints"] or 0
                elif task.estimated_hours:
                    # Convert hours to story points (rough estimate: 8 hours = 1 point)
                    story_points = task.estimated_hours / 8
                
                # Determine if completed
                status_lower = (task.status or "").lower()
                is_completed = any(keyword in status_lower for keyword in ["done", "closed", "completed", "resolved"])
                
                tasks_data.append({
                    "id": task.id,
                    "title": task.title,
                    "story_points": story_points,
                    "status": task.status,
                    "completed": is_completed,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                })
            
            return {
                "sprint": {
                    "id": sprint.id,
                    "name": sprint.name,
                    "start_date": sprint.start_date.isoformat() if sprint.start_date else None,
                    "end_date": sprint.end_date.isoformat() if sprint.end_date else None,
                    "status": sprint.status,
                },
                "tasks": tasks_data,
                "scope_changes": [],  # TODO: Track scope changes if provider supports it
            }
        
        except Exception as e:
            logger.error(f"[PMProviderAnalyticsAdapter] Error fetching burndown data: {e}", exc_info=True)
            raise
    
    async def get_velocity_data(
        self,
        project_id: str,
        num_sprints: int = 6
    ) -> List[Dict[str, Any]]:
        """Fetch velocity data from PM provider"""
        logger.info(f"[PMProviderAnalyticsAdapter] Fetching velocity data: project={project_id}, num_sprints={num_sprints}")
        
        try:
            # Get recent sprints
            all_sprints = await self.provider.list_sprints(project_id=project_id)
            
            # Sort by start_date (most recent first) and take num_sprints
            sorted_sprints = sorted(
                [s for s in all_sprints if s.start_date],
                key=lambda s: s.start_date,
                reverse=True
            )[:num_sprints]
            
            # Reverse to show oldest first
            sorted_sprints.reverse()
            
            logger.info(f"[PMProviderAnalyticsAdapter] Found {len(sorted_sprints)} sprints for velocity")
            
            velocity_data = []
            
            for sprint in sorted_sprints:
                # Get tasks for this sprint
                all_tasks = await self.provider.list_tasks(project_id=project_id)
                sprint_tasks = [t for t in all_tasks if t.sprint_id == sprint.id]
                
                # Calculate planned and completed
                planned_points = 0
                completed_points = 0
                planned_count = len(sprint_tasks)
                completed_count = 0
                
                for task in sprint_tasks:
                    # Extract story points
                    story_points = 0
                    if task.raw_data and "storyPoints" in task.raw_data:
                        story_points = task.raw_data["storyPoints"] or 0
                    elif task.estimated_hours:
                        story_points = task.estimated_hours / 8
                    
                    planned_points += story_points
                    
                    # Check if completed
                    status_lower = (task.status or "").lower()
                    is_completed = any(keyword in status_lower for keyword in ["done", "closed", "completed", "resolved"])
                    
                    if is_completed:
                        completed_points += story_points
                        completed_count += 1
                
                velocity_data.append({
                    "name": sprint.name,
                    "start_date": sprint.start_date.isoformat() if sprint.start_date else None,
                    "end_date": sprint.end_date.isoformat() if sprint.end_date else None,
                    "planned_points": planned_points,
                    "completed_points": completed_points,
                    "planned_count": planned_count,
                    "completed_count": completed_count,
                })
            
            return velocity_data
        
        except Exception as e:
            logger.error(f"[PMProviderAnalyticsAdapter] Error fetching velocity data: {e}", exc_info=True)
            raise
    
    async def get_sprint_report_data(
        self,
        sprint_id: str,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch sprint report data from PM provider"""
        logger.info(f"[PMProviderAnalyticsAdapter] Fetching sprint report data: sprint={sprint_id}")
        
        try:
            # Get sprint
            sprint = await self.provider.get_sprint(sprint_id)
            if not sprint:
                raise ValueError(f"Sprint {sprint_id} not found")
            
            # Get all tasks in sprint
            all_tasks = await self.provider.list_tasks(project_id=project_id or sprint.project_id)
            sprint_tasks = [t for t in all_tasks if t.sprint_id == sprint_id]
            
            # Get team members (unique assignees)
            team_members = list(set(t.assignee_id for t in sprint_tasks if t.assignee_id))
            
            # Categorize tasks
            completed_tasks = []
            incomplete_tasks = []
            
            for task in sprint_tasks:
                status_lower = (task.status or "").lower()
                is_completed = any(keyword in status_lower for keyword in ["done", "closed", "completed", "resolved"])
                
                task_data = {
                    "id": task.id,
                    "title": task.title,
                    "status": task.status,
                    "assignee_id": task.assignee_id,
                    "priority": task.priority,
                    "type": task.raw_data.get("type") if task.raw_data else "Task",
                }
                
                if is_completed:
                    completed_tasks.append(task_data)
                else:
                    incomplete_tasks.append(task_data)
            
            return {
                "sprint": {
                    "id": sprint.id,
                    "name": sprint.name,
                    "start_date": sprint.start_date.isoformat() if sprint.start_date else None,
                    "end_date": sprint.end_date.isoformat() if sprint.end_date else None,
                    "status": sprint.status,
                    "goal": sprint.goal,
                },
                "tasks": sprint_tasks,
                "team_members": team_members,
                "completed_tasks": completed_tasks,
                "incomplete_tasks": incomplete_tasks,
                "added_tasks": [],  # TODO: Track if provider supports it
                "removed_tasks": [],  # TODO: Track if provider supports it
            }
        
        except Exception as e:
            logger.error(f"[PMProviderAnalyticsAdapter] Error fetching sprint report data: {e}", exc_info=True)
            raise
    
    async def get_cfd_data(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Fetch CFD data from PM provider"""
        logger.info(f"[PMProviderAnalyticsAdapter] Fetching CFD data: project={project_id}, days_back={days_back}")
        
        try:
            # Get tasks
            all_tasks = await self.provider.list_tasks(project_id=project_id)
            
            if sprint_id:
                all_tasks = [t for t in all_tasks if t.sprint_id == sprint_id]
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Get available statuses from tasks
            statuses = list(set(t.status for t in all_tasks if t.status))
            
            # Order statuses (common workflow)
            status_order = ["todo", "to do", "new", "in progress", "in review", "testing", "done", "closed", "completed"]
            def status_sort_key(status):
                status_lower = status.lower()
                for i, s in enumerate(status_order):
                    if s in status_lower:
                        return i
                return 999
            
            statuses.sort(key=status_sort_key)
            
            # Build work items with status history
            work_items = []
            for task in all_tasks:
                # Since we don't have full history, simulate it
                # Use created_at as initial status date
                status_history = []
                
                if task.created_at:
                    # Initial status (assume "To Do")
                    status_history.append({
                        "date": task.created_at.isoformat(),
                        "status": "To Do"
                    })
                
                # Current status
                if task.status and task.updated_at:
                    status_history.append({
                        "date": task.updated_at.isoformat(),
                        "status": task.status
                    })
                elif task.status and task.created_at:
                    status_history.append({
                        "date": task.created_at.isoformat(),
                        "status": task.status
                    })
                
                work_items.append({
                    "id": task.id,
                    "title": task.title,
                    "created_date": task.created_at.isoformat() if task.created_at else start_date.isoformat(),
                    "status_history": status_history if status_history else [
                        {"date": start_date.isoformat(), "status": task.status or "To Do"}
                    ],
                })
            
            return {
                "work_items": work_items,
                "start_date": start_date,
                "end_date": end_date,
                "statuses": statuses if statuses else ["To Do", "In Progress", "Done"],
            }
        
        except Exception as e:
            logger.error(f"[PMProviderAnalyticsAdapter] Error fetching CFD data: {e}", exc_info=True)
            raise
    
    async def get_cycle_time_data(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        days_back: int = 60
    ) -> List[Dict[str, Any]]:
        """Fetch cycle time data from PM provider"""
        logger.info(f"[PMProviderAnalyticsAdapter] Fetching cycle time data: project={project_id}, days_back={days_back}")
        
        try:
            # Get tasks
            all_tasks = await self.provider.list_tasks(project_id=project_id)
            
            if sprint_id:
                all_tasks = [t for t in all_tasks if t.sprint_id == sprint_id]
            
            # Filter completed tasks in the date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            cycle_time_data = []
            
            for task in all_tasks:
                # Only include completed tasks
                status_lower = (task.status or "").lower()
                is_completed = any(keyword in status_lower for keyword in ["done", "closed", "completed", "resolved"])
                
                if not is_completed or not task.completed_at:
                    continue
                
                # Check if completed in date range
                if task.completed_at < start_date or task.completed_at > end_date:
                    continue
                
                # Calculate cycle time
                start_date_task = task.start_date or task.created_at
                if not start_date_task:
                    continue
                
                # Convert to datetime if date
                if isinstance(start_date_task, date) and not isinstance(start_date_task, datetime):
                    start_date_task = datetime.combine(start_date_task, datetime.min.time())
                
                cycle_time_days = (task.completed_at - start_date_task).days
                
                # Get task type
                task_type = "Task"
                if task.raw_data and "type" in task.raw_data:
                    task_type = task.raw_data["type"]
                
                cycle_time_data.append({
                    "id": task.id,
                    "title": task.title,
                    "type": task_type,
                    "start_date": start_date_task.isoformat(),
                    "completion_date": task.completed_at.isoformat(),
                    "cycle_time_days": max(cycle_time_days, 0),  # Ensure non-negative
                })
            
            logger.info(f"[PMProviderAnalyticsAdapter] Found {len(cycle_time_data)} completed tasks for cycle time")
            
            return cycle_time_data
        
        except Exception as e:
            logger.error(f"[PMProviderAnalyticsAdapter] Error fetching cycle time data: {e}", exc_info=True)
            raise
    
    async def get_work_distribution_data(
        self,
        project_id: str,
        sprint_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch work distribution data from PM provider"""
        logger.info(f"[PMProviderAnalyticsAdapter] Fetching work distribution data: project={project_id}")
        
        try:
            # Get tasks
            all_tasks = await self.provider.list_tasks(project_id=project_id)
            
            if sprint_id:
                all_tasks = [t for t in all_tasks if t.sprint_id == sprint_id]
            
            # Transform tasks
            work_items = []
            for task in all_tasks:
                # Extract story points
                story_points = 0
                if task.raw_data and "storyPoints" in task.raw_data:
                    story_points = task.raw_data["storyPoints"] or 0
                elif task.estimated_hours:
                    story_points = task.estimated_hours / 8
                
                # Get task type
                task_type = "Task"
                if task.raw_data and "type" in task.raw_data:
                    task_type = task.raw_data["type"]
                
                # Get assignee name
                assignee = task.assignee_id or "Unassigned"
                
                work_items.append({
                    "id": task.id,
                    "title": task.title,
                    "assignee": assignee,
                    "priority": task.priority or "Medium",
                    "type": task_type,
                    "status": task.status or "To Do",
                    "story_points": story_points,
                })
            
            logger.info(f"[PMProviderAnalyticsAdapter] Found {len(work_items)} tasks for work distribution")
            
            return work_items
        
        except Exception as e:
            logger.error(f"[PMProviderAnalyticsAdapter] Error fetching work distribution data: {e}", exc_info=True)
            raise
    
    async def get_issue_trend_data(
        self,
        project_id: str,
        days_back: int = 30,
        sprint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch issue trend data from PM provider"""
        logger.info(f"[PMProviderAnalyticsAdapter] Fetching issue trend data: project={project_id}, days_back={days_back}")
        
        try:
            # Get tasks
            all_tasks = await self.provider.list_tasks(project_id=project_id)
            
            if sprint_id:
                all_tasks = [t for t in all_tasks if t.sprint_id == sprint_id]
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Transform tasks
            work_items = []
            for task in all_tasks:
                # Get task type
                task_type = "Task"
                if task.raw_data and "type" in task.raw_data:
                    task_type = task.raw_data["type"]
                
                work_items.append({
                    "id": task.id,
                    "title": task.title,
                    "type": task_type,
                    "created_date": task.created_at.isoformat() if task.created_at else start_date.isoformat(),
                    "completion_date": task.completed_at.isoformat() if task.completed_at else None,
                })
            
            logger.info(f"[PMProviderAnalyticsAdapter] Found {len(work_items)} tasks for issue trend")
            
            return {
                "work_items": work_items,
                "start_date": start_date,
                "end_date": end_date,
            }
        
        except Exception as e:
            logger.error(f"[PMProviderAnalyticsAdapter] Error fetching issue trend data: {e}", exc_info=True)
            raise

