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
    
    def __init__(self, db_session=None, llm=None):
        """Initialize sprint planner
        
        Args:
            db_session: Database session for querying tasks and team
            llm: Optional LLM instance for generating sprint plans
        """
        self.db_session = db_session
        self.llm = llm
    
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
        logger.info(f"Sprint capacity: {len(team_members)} members × {duration_days} days × {team_capacity_hours_per_day}h = {total_capacity}h")
        
        # Try LLM-based planning if LLM is available
        if self.llm:
            try:
                logger.info("Using LLM for sprint planning")
                sprint_plan = await self._generate_sprint_plan_with_llm(
                    available_tasks=available_tasks,
                    team_members=team_members,
                    total_capacity=total_capacity,
                    duration_days=duration_days,
                    project_id=project_id,
                    default_sprint_name=sprint_name
                )
                # Convert LLM plan to SprintTask objects
                selected_tasks = []
                for task_data in sprint_plan.get("selected_tasks", []):
                    task = SprintTask(
                        task_id=task_data["task_id"],
                        title=task_data["title"],
                        estimated_hours=task_data["estimated_hours"],
                        priority=task_data["priority"],
                        assigned_to=task_data.get("assigned_to")
                    )
                    selected_tasks.append(task)
                
                # Update sprint_name if LLM generated one
                sprint_name = sprint_plan.get("sprint_name", sprint_name)
                total_hours = sprint_plan.get("summary", {}).get("planned_hours", 0.0)
                assigned_tasks = selected_tasks
            except Exception as e:
                logger.warning(f"LLM sprint planning failed: {e}, falling back to rule-based")
                # Fall through to rule-based planning
                selected_tasks, total_hours = self._select_tasks_for_sprint(
                    available_tasks, total_capacity
                )
                assigned_tasks = self._assign_tasks_to_team(
                    selected_tasks, team_members, team_capacity_hours_per_day, duration_days
                )
        else:
            # Select and assign tasks using rule-based logic
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
        
        logger.info(f"Selecting tasks from {len(sorted_tasks)} available tasks with capacity {total_capacity}h")
        
        for idx, task_data in enumerate(sorted_tasks):
            estimated = task_data["estimated_hours"]
            
            # Skip tasks that are too large (likely parent tasks)
            # A single task shouldn't exceed half the sprint capacity
            if estimated > total_capacity * 0.5:
                logger.info(f"Skipping task '{task_data['title']}' - too large ({estimated}h > {total_capacity * 0.5}h)")
                continue
            
            # Check if we have capacity
            if total_hours + estimated <= total_capacity:
                selected.append(SprintTask(
                    task_id=task_data["id"],
                    title=task_data["title"],
                    estimated_hours=estimated,
                    priority=task_data["priority"]
                ))
                total_hours += estimated
                logger.info(f"Added task '{task_data['title']}' ({estimated}h). Total: {total_hours}h")
            else:
                # Try to fit a partial task
                remaining_capacity = total_capacity - total_hours
                if remaining_capacity > 0:
                    logger.info(f"Task '{task_data['title']}' ({estimated}h) not added - remaining capacity: {remaining_capacity}h")
                break
        
        logger.info(f"Selected {len(selected)} tasks totaling {total_hours}h")
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
    
    async def _generate_sprint_plan_with_llm(
        self,
        available_tasks: List[Dict[str, Any]],
        team_members: List[str],
        total_capacity: float,
        duration_days: int,
        project_id: str,
        default_sprint_name: str = ""
    ) -> Dict[str, Any]:
        """
        Generate sprint plan using LLM with task selection and assignment
        """
        try:
            prompt = self._build_sprint_prompt(
                available_tasks=available_tasks,
                team_members=team_members,
                total_capacity=total_capacity,
                duration_days=duration_days
            )
            
            # Call LLM to generate sprint plan
            logger.info("Invoking LLM for sprint planning...")
            response = await self.llm.ainvoke(prompt)
            
            # Parse response
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            logger.info(f"LLM response received (length: {len(response_text)})")
            logger.debug(f"LLM response: {response_text[:1000]}")
            
            # Try to extract JSON structure
            import json
            import re
            
            # Look for JSON in the response - try to find the outermost object
            json_block_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_block_match:
                try:
                    sprint_json = json.loads(json_block_match.group(1))
                    logger.info(f"Successfully parsed JSON block. Sprint: {sprint_json.get('sprint_name')}")
                    return sprint_json
                except json.JSONDecodeError:
                    logger.warning("Could not parse JSON block")
            
            # If no JSON block found, try to find outermost JSON object
            brace_count = 0
            start_idx = response_text.find('{')
            if start_idx != -1:
                for i in range(start_idx, len(response_text)):
                    if response_text[i] == '{':
                        brace_count += 1
                    elif response_text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            try:
                                sprint_json = json.loads(response_text[start_idx:i+1])
                                logger.info(f"Successfully parsed outermost JSON. Sprint: {sprint_json.get('sprint_name')}")
                                return sprint_json
                            except json.JSONDecodeError:
                                logger.warning("Could not parse outermost JSON object")
                            break
            
            logger.error("Could not find valid JSON in LLM response")
            logger.debug(f"Response text (first 1000 chars): {response_text[:1000]}")
            raise ValueError("No valid JSON found in LLM response")
                
        except Exception as e:
            logger.error(f"LLM sprint planning failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _build_sprint_prompt(
        self,
        available_tasks: List[Dict[str, Any]],
        team_members: List[str],
        total_capacity: float,
        duration_days: int
    ) -> List[Dict[str, str]]:
        """Build prompt for LLM to generate sprint plan"""
        from src.prompts.template import get_prompt_template
        
        # Load the sprint planner prompt template
        system_prompt = get_prompt_template("sprint_planner", locale="en-US")
        
        # Build user message with task details
        tasks_section = "\n".join([
            f"- ID: {task['id']}, Title: {task['title']}, Hours: {task['estimated_hours']}, Priority: {task['priority']}"
            for task in available_tasks
        ])
        
        user_message = f"""Create a sprint plan for these available tasks:

Available Tasks ({len(available_tasks)} total):
{tasks_section}

Team Members: {', '.join(team_members)}
Total Sprint Capacity: {total_capacity} hours
Duration: {duration_days} days
Capacity per member per day: {total_capacity / (len(team_members) * duration_days) if len(team_members) > 0 else 0:.1f} hours

Please select tasks that fit within the capacity and create a goal-oriented sprint name based on the selected tasks."""
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

