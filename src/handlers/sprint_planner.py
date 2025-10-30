"""
Sprint Planning Handler

Creates sprint plans with task assignments, capacity checking,
and timeline optimization.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class SprintTask:
    """Represents a task in a sprint"""
    task_id: str
    title: str
    estimated_hours: float
    priority: str
    assigned_to: Optional[str] = None
    dependencies: List[str] = None


@dataclass
class SprintPlan:
    """Represents a sprint plan"""
    sprint_name: str
    start_date: datetime
    end_date: datetime
    duration_days: int
    capacity_hours: float
    tasks: List[SprintTask]
    team_members: List[str]


class SprintPlanner:
    """Creates sprint plans for projects"""
    
    def __init__(self, db_session=None):
        """Initialize sprint planner
        
        Args:
            db_session: Database session for querying tasks and team
        """
        self.db_session = db_session
    
    async def plan_sprint(
        self,
        project_id: str,
        sprint_name: str,
        duration_weeks: int = 2,
        start_date: Optional[datetime] = None,
        team_capacity_hours_per_day: float = 6.0,
        working_days_per_week: int = 5
    ) -> Dict[str, Any]:
        """
        Plan a sprint with task assignments
        
        Args:
            project_id: ID of the project
            project_name: Name of the sprint
            duration_weeks: Duration in weeks (default: 2)
            start_date: Start date (default: today)
            team_capacity_hours_per_day: Hours per team member per day
            working_days_per_week: Working days per week
            
        Returns:
            Sprint plan with task assignments
        """
        logger.info(f"Planning sprint: {sprint_name}")
        
        # Calculate dates
        if not start_date:
            start_date = datetime.now()
        
        end_date = start_date + timedelta(weeks=duration_weeks)
        duration_days = duration_weeks * working_days_per_week
        
        # Get available tasks from project
        available_tasks = await self._get_available_tasks(project_id)
        
        if not available_tasks:
            return {
                "sprint_name": sprint_name,
                "message": "No available tasks found for this project",
                "tasks_assigned": 0
            }
        
        # Get team members
        team_members = await self._get_team_members(project_id)
        
        # Calculate capacity
        total_capacity = len(team_members) * duration_days * team_capacity_hours_per_day
        
        # Select and assign tasks
        selected_tasks, total_hours = self._select_tasks_for_sprint(
            available_tasks, total_capacity
        )
        
        # Assign tasks to team members
        assigned_tasks = self._assign_tasks_to_team(
            selected_tasks, team_members, team_capacity_hours_per_day, duration_days
        )
        
        # Save sprint to database
        sprint_id = None
        if self.db_session:
            try:
                from database.orm_models import Sprint, SprintTask
                from uuid import UUID
                
                # Create sprint record
                sprint = Sprint(
                    project_id=UUID(project_id),
                    name=sprint_name,
                    start_date=start_date.date(),
                    end_date=end_date.date(),
                    duration_weeks=duration_weeks,
                    duration_days=duration_days,
                    capacity_hours=total_capacity,
                    planned_hours=total_hours,
                    utilization=(total_hours / total_capacity * 100) if total_capacity > 0 else 0,
                    status='planned'
                )
                self.db_session.add(sprint)
                self.db_session.commit()
                self.db_session.refresh(sprint)
                sprint_id = str(sprint.id)
                
                # Create sprint task records
                for task in assigned_tasks:
                    sprint_task = SprintTask(
                        sprint_id=UUID(sprint_id),
                        task_id=UUID(task.task_id),
                        assigned_to_name=task.assigned_to,
                        capacity_used=task.estimated_hours
                    )
                    self.db_session.add(sprint_task)
                
                self.db_session.commit()
                logger.info(f"Sprint saved to database: {sprint_id}")
            except Exception as e:
                logger.error(f"Could not save sprint to database: {e}")
                import traceback
                logger.error(traceback.format_exc())
                self.db_session.rollback()
        
        return {
            "sprint_id": sprint_id,
            "sprint_name": sprint_name,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "duration_weeks": duration_weeks,
            "duration_days": duration_days,
            "total_capacity_hours": total_capacity,
            "planned_hours": total_hours,
            "utilization": (total_hours / total_capacity * 100) if total_capacity > 0 else 0,
            "team_members": team_members,
            "tasks_assigned": len(assigned_tasks),
            "tasks": [
                {
                    "task_id": task.task_id,
                    "title": task.title,
                    "estimated_hours": task.estimated_hours,
                    "priority": task.priority,
                    "assigned_to": task.assigned_to
                }
                for task in assigned_tasks
            ]
        }
    
    async def _get_available_tasks(self, project_id: str) -> List[Dict[str, Any]]:
        """Get available (unassigned) tasks from project"""
        if not self.db_session:
            logger.warning("No db_session available for fetching tasks")
            return []
        
        try:
            from database.crud import get_tasks_by_project
            from uuid import UUID
            
            logger.info(f"Fetching tasks for project_id: {project_id}")
            tasks = get_tasks_by_project(self.db_session, UUID(project_id), status="todo")
            logger.info(f"Found {len(tasks)} tasks with status='todo'")
            
            result = [
                {
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "estimated_hours": task.estimated_hours or 8.0,
                    "priority": task.priority or "medium"
                }
                for task in tasks
            ]
            logger.info(f"Returning {len(result)} tasks for sprint planning")
            return result
        except Exception as e:
            logger.error(f"Could not fetch tasks: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def _get_team_members(self, project_id: str) -> List[str]:
        """Get team members for the project"""
        if not self.db_session:
            return ["Team Member 1", "Team Member 2"]
        
        try:
            from database.crud import get_team_members_by_project
            from uuid import UUID
            
            members = get_team_members_by_project(self.db_session, UUID(project_id))
            
            # Get user names from member objects
            if members:
                from database.crud import get_user
                user_names = []
                for member in members:
                    user = get_user(self.db_session, member.user_id)
                    if user:
                        user_names.append(user.name)
                return user_names if user_names else ["Team Member 1"]
            return ["Team Member 1"]
        except Exception as e:
            logger.error(f"Could not fetch team members: {e}")
            return ["Team Member 1"]
    
    def _select_tasks_for_sprint(
        self, 
        available_tasks: List[Dict[str, Any]], 
        total_capacity: float
    ) -> tuple[List[SprintTask], float]:
        """
        Select tasks for the sprint based on capacity and priority
        
        Returns tuple of (selected_tasks, total_hours)
        """
        # Sort by priority (high -> medium -> low)
        priority_order = {"high": 0, "medium": 1, "low": 2}
        sorted_tasks = sorted(
            available_tasks, 
            key=lambda t: priority_order.get(t["priority"], 1)
        )
        
        selected = []
        total_hours = 0.0
        
        for task_data in sorted_tasks:
            estimated = task_data["estimated_hours"]
            
            # Check if we have capacity
            if total_hours + estimated <= total_capacity:
                selected.append(SprintTask(
                    task_id=task_data["id"],
                    title=task_data["title"],
                    estimated_hours=estimated,
                    priority=task_data["priority"]
                ))
                total_hours += estimated
            else:
                # Try to fit a partial task
                remaining_capacity = total_capacity - total_hours
                if remaining_capacity > 0:
                    logger.info(f"Partial task '{task_data['title']}' not added due to capacity limits")
                break
        
        return selected, total_hours
    
    def _assign_tasks_to_team(
        self,
        tasks: List[SprintTask],
        team_members: List[str],
        capacity_per_member_per_day: float,
        days_in_sprint: int
    ) -> List[SprintTask]:
        """
        Assign tasks to team members based on availability
        
        Uses a simple round-robin approach with capacity consideration
        """
        if not team_members:
            return tasks
        
        # Calculate capacity per member
        capacity_per_member = capacity_per_member_per_day * days_in_sprint
        
        # Track assigned hours per member
        member_workload = {member: 0.0 for member in team_members}
        
        # Assign tasks
        for task in tasks:
            # Find member with least workload
            assigned_member = min(member_workload.keys(), key=lambda m: member_workload[m])
            
            # Check capacity
            if member_workload[assigned_member] + task.estimated_hours <= capacity_per_member:
                task.assigned_to = assigned_member
                member_workload[assigned_member] += task.estimated_hours
            else:
                # Look for another member with capacity
                assigned = False
                for member in team_members:
                    if member_workload[member] + task.estimated_hours <= capacity_per_member:
                        task.assigned_to = member
                        member_workload[member] += task.estimated_hours
                        assigned = True
                        break
                
                # If no one has capacity, assign to least loaded member
                if not assigned:
                    task.assigned_to = min(member_workload.keys(), key=lambda m: member_workload[m])
                    member_workload[task.assigned_to] += task.estimated_hours
        
        return tasks

