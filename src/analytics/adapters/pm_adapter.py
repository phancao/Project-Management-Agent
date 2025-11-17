# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
PM Provider Analytics Adapter

Fetches real data from PM providers (OpenProject, JIRA) and transforms it
for analytics calculators.

Uses TaskStatusResolver to handle provider-specific status logic.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
from collections import defaultdict

from src.pm_providers.base import BasePMProvider
from src.pm_providers.models import PMTask, PMSprint, PMProject
from .base import BaseAnalyticsAdapter
from .task_status_resolver import TaskStatusResolver, create_task_status_resolver

logger = logging.getLogger(__name__)


class PMProviderAnalyticsAdapter(BaseAnalyticsAdapter):
    """
    Analytics adapter that fetches data from PM providers.
    
    Uses TaskStatusResolver to handle provider-specific status logic.
    """
    
    def __init__(self, provider: BasePMProvider):
        """
        Initialize adapter with a PM provider.
        
        Args:
            provider: PM provider instance (OpenProject, JIRA, etc.)
        """
        self.provider = provider
        
        # Create appropriate task status resolver based on provider type
        provider_type = getattr(
            getattr(provider, "config", None),
            "provider_type",
            provider.__class__.__name__
        )
        self.status_resolver: TaskStatusResolver = create_task_status_resolver(provider_type)
        
        logger.info(f"[PMProviderAnalyticsAdapter] Created with resolver for provider: {provider_type}")
    
    def _extract_project_key(self, project_id: str) -> str:
        """
        Extract the project key from a composite project ID.
        
        Args:
            project_id: Either "provider_uuid:project_key" or just "project_key"
        
        Returns:
            The project key portion
        """
        if ":" in project_id:
            return project_id.split(":", 1)[1]
        return project_id

    async def get_burndown_data(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        scope_type: str = "story_points"
    ) -> Dict[str, Any]:
        """Fetch burndown data from PM provider"""
        logger.info(f"[PMProviderAnalyticsAdapter] Fetching burndown data: project={project_id}, sprint={sprint_id}")
        
        project_key = self._extract_project_key(project_id)

        try:
            # Get sprint info
            if not sprint_id:
                # Get active sprint
                sprints = await self.provider.list_sprints(
                    project_id=project_key, state="active"
                )
                if not sprints:
                    # Fallback to any sprint
                    sprints = await self.provider.list_sprints(project_id=project_key)
                if not sprints:
                    # No sprints found - return None to signal fallback to mock data
                    logger.warning(f"[PMProviderAnalyticsAdapter] No sprints found for project {project_id}, will use mock data")
                    return None
                sprint = sprints[0]
                sprint_id = sprint.id
                logger.info(f"[PMProviderAnalyticsAdapter] Using active sprint: {sprint.name} (id={sprint_id})")
            else:
                try:
                    sprint = await self.provider.get_sprint(sprint_id)
                    if sprint:
                        logger.info(f"[PMProviderAnalyticsAdapter] Found sprint: {sprint.name} (id={sprint_id})")
                except NotImplementedError as exc:
                    provider_name = getattr(
                        getattr(self.provider, "config", None), "provider_type", self.provider.__class__.__name__
                    )
                    raise NotImplementedError(
                        f"Sprint lookup not supported for provider '{provider_name}'. "
                        "Sprint analytics require get_sprint implementation."
                    ) from exc
                except Exception as exc:
                    logger.warning(
                        "[PMProviderAnalyticsAdapter] get_sprint failed for %s: %s",
                        sprint_id,
                        exc,
                    )
                    raise
            
            if not sprint:
                raise ValueError(f"Sprint {sprint_id} not found")
            
            # Get all tasks in the sprint
            all_tasks = await self.provider.list_tasks(project_id=project_key)
            
            # Debug logging
            logger.info(f"[PMProviderAnalyticsAdapter] Looking for sprint_id={sprint_id} (type: {type(sprint_id).__name__})")
            logger.info(f"[PMProviderAnalyticsAdapter] Found {len(all_tasks)} total tasks in project")
            
            # Log sprint_ids from tasks for debugging
            task_sprint_ids = [str(t.sprint_id) if t.sprint_id else "None" for t in all_tasks[:10]]
            logger.info(f"[PMProviderAnalyticsAdapter] Sample task sprint_ids: {task_sprint_ids}")
            
            # Compare sprint_id as strings to handle type mismatches
            sprint_id_str = str(sprint_id) if sprint_id else None
            sprint_tasks = [
                t for t in all_tasks 
                if (t.sprint_id and str(t.sprint_id) == sprint_id_str) or 
                   (sprint_id_str and t.sprint_id == sprint_id)
            ]
            
            logger.info(f"[PMProviderAnalyticsAdapter] Found {len(sprint_tasks)} tasks in sprint {sprint_id}")
            
            # If no tasks found, log more details
            if len(sprint_tasks) == 0 and len(all_tasks) > 0:
                # Log detailed info about first few tasks
                logger.warning(
                    f"[PMProviderAnalyticsAdapter] No tasks found for sprint {sprint_id}. "
                    f"Total tasks: {len(all_tasks)}"
                )
                # Log sprint_ids from all tasks
                all_sprint_ids = [str(t.sprint_id) if t.sprint_id else "None" for t in all_tasks]
                logger.warning(
                    f"[PMProviderAnalyticsAdapter] All task sprint_ids: {all_sprint_ids}"
                )
                # Log raw data from first task to debug version link
                if all_tasks[0].raw_data:
                    task_raw = all_tasks[0].raw_data
                    version_link = task_raw.get("_links", {}).get("version")
                    version_embedded = task_raw.get("_embedded", {}).get("version")
                    logger.warning(
                        f"[PMProviderAnalyticsAdapter] Sample task raw data - "
                        f"_links.version: {version_link}, "
                        f"_embedded.version: {version_embedded is not None if version_embedded else False}"
                    )
            
            # Transform tasks for burndown calculator using status resolver
            tasks_data = []
            for task in sprint_tasks:
                # Use resolver to extract story points
                story_points = self.status_resolver.extract_story_points(task)
                
                # Use resolver to determine if burndowned
                is_burndowned = self.status_resolver.is_burndowned(task)
                
                # Get completion date from resolver
                completion_date = self.status_resolver.get_completion_date(task)
                
                tasks_data.append({
                    "id": task.id,
                    "title": task.title,
                    "story_points": story_points,
                    "status": task.status,
                    "completed": is_burndowned,
                    "completed_at": completion_date.isoformat() if completion_date else None,
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
        
        project_key = self._extract_project_key(project_id)

        try:
            # Get recent sprints
            all_sprints = await self.provider.list_sprints(project_id=project_key)
            
            if not all_sprints:
                logger.warning(f"[PMProviderAnalyticsAdapter] No sprints found for project {project_id}")
                return None
            
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
            
            all_tasks = await self.provider.list_tasks(project_id=project_key)
            
            for sprint in sorted_sprints:
                sprint_tasks = [t for t in all_tasks if t.sprint_id == sprint.id]
                
                # Calculate planned and completed
                planned_points = 0
                completed_points = 0
                planned_count = len(sprint_tasks)
                completed_count = 0
                
                for task in sprint_tasks:
                    # Use resolver to extract story points
                    story_points = self.status_resolver.extract_story_points(task)
                    
                    planned_points += story_points
                    
                    # Use resolver to check if completed
                    is_completed = self.status_resolver.is_completed(task)
                    
                    if is_completed:
                        completed_points += story_points
                        completed_count += 1
                
                velocity_data.append({
                    "sprint_id": sprint.id,
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
            try:
                sprint = await self.provider.get_sprint(sprint_id)
            except NotImplementedError as exc:
                provider_name = getattr(
                    getattr(self.provider, "config", None), "provider_type", self.provider.__class__.__name__
                )
                raise NotImplementedError(
                    f"Sprint lookup not supported for provider '{provider_name}'. "
                    "Sprint analytics require get_sprint implementation."
                ) from exc
            if not sprint:
                logger.warning(f"[PMProviderAnalyticsAdapter] Sprint {sprint_id} not found")
                return None
            
            # Get all tasks in sprint
            proj_id = project_id or sprint.project_id
            project_key = self._extract_project_key(proj_id)
            all_tasks = await self.provider.list_tasks(project_id=project_key)
            sprint_tasks = [t for t in all_tasks if t.sprint_id == sprint_id]
            
            # Get team members (unique assignees)
            team_members = list(set(t.assignee_id for t in sprint_tasks if t.assignee_id))
            
            # Categorize tasks
            completed_tasks = []
            incomplete_tasks = []
            
            for task in sprint_tasks:
                # Use resolver to check completion
                is_completed = self.status_resolver.is_completed(task)
                
                # Use resolver to get task type
                task_type = self.status_resolver.get_task_type(task)
                
                task_data = {
                    "id": task.id,
                    "title": task.title,
                    "status": task.status,
                    "assignee_id": task.assignee_id,
                    "priority": task.priority,
                    "type": task_type,
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
            project_key = self._extract_project_key(project_id)
            all_tasks = await self.provider.list_tasks(project_id=project_key)
            
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
            
            # Build work items with status history using resolver
            work_items = []
            for task in all_tasks:
                # Use resolver to get status history
                status_history = self.status_resolver.get_status_history(task)
                
                # If no history, create basic one
                if not status_history:
                    if task.created_at:
                        status_history.append({
                            "date": task.created_at.isoformat(),
                            "status": task.status or "To Do"
                        })
                    else:
                        status_history.append({
                            "date": start_date.isoformat(),
                            "status": task.status or "To Do"
                        })
                
                work_items.append({
                    "id": task.id,
                    "title": task.title,
                    "created_date": task.created_at.isoformat() if task.created_at else start_date.isoformat(),
                    "status_history": status_history,
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
            project_key = self._extract_project_key(project_id)
            all_tasks = await self.provider.list_tasks(project_id=project_key)
            
            if sprint_id:
                all_tasks = [t for t in all_tasks if t.sprint_id == sprint_id]
            
            # Filter completed tasks in the date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            cycle_time_data = []
            
            for task in all_tasks:
                # Use resolver to check if completed
                is_completed = self.status_resolver.is_completed(task)
                
                if not is_completed:
                    continue
                
                # Get completion date from resolver
                completion_date = self.status_resolver.get_completion_date(task)
                if not completion_date:
                    continue
                
                # Check if completed in date range
                if completion_date < start_date or completion_date > end_date:
                    continue
                
                # Get start date from resolver
                start_date_task = self.status_resolver.get_start_date(task)
                if not start_date_task:
                    continue
                
                # Calculate cycle time
                cycle_time_days = (completion_date - start_date_task).days
                
                # Get task type from resolver
                task_type = self.status_resolver.get_task_type(task)
                
                cycle_time_data.append({
                    "id": task.id,
                    "title": task.title,
                    "type": task_type,
                    "start_date": start_date_task.isoformat(),
                    "completion_date": completion_date.isoformat(),
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
            project_key = self._extract_project_key(project_id)
            all_tasks = await self.provider.list_tasks(project_id=project_key)
            
            if sprint_id:
                all_tasks = [t for t in all_tasks if t.sprint_id == sprint_id]
            
            # Transform tasks using resolver
            work_items = []
            assignee_name_cache: Dict[str, str] = {}
            for task in all_tasks:
                # Use resolver to extract story points
                story_points = self.status_resolver.extract_story_points(task)
                
                # Use resolver to get task type
                task_type = self.status_resolver.get_task_type(task)
                
                # Get assignee name
                assignee_id = task.assignee_id
                if assignee_id:
                    if assignee_id not in assignee_name_cache:
                        display_name = assignee_id
                        try:
                            user = await self.provider.get_user(assignee_id)
                            if user and user.name:
                                display_name = user.name
                        except Exception:
                            pass
                        assignee_name_cache[assignee_id] = display_name
                    assignee = assignee_name_cache[assignee_id]
                else:
                    assignee = "Unassigned"

                work_items.append({
                    "id": task.id,
                    "title": task.title,
                    "assignee": assignee,
                    "assignee_id": assignee_id,
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
            project_key = self._extract_project_key(project_id)
            all_tasks = await self.provider.list_tasks(project_id=project_key)
            
            if sprint_id:
                all_tasks = [t for t in all_tasks if t.sprint_id == sprint_id]
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Transform tasks using resolver
            work_items = []
            for task in all_tasks:
                # Use resolver to get task type
                task_type = self.status_resolver.get_task_type(task)
                
                # Use resolver to get completion date
                completion_date = self.status_resolver.get_completion_date(task)
                
                work_items.append({
                    "id": task.id,
                    "title": task.title,
                    "type": task_type,
                    "created_date": task.created_at.isoformat() if task.created_at else start_date.isoformat(),
                    "completion_date": completion_date.isoformat() if completion_date else None,
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

