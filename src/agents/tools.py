"""
Project Management Agent Tools
Concrete implementations of tools that agents can use
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.utils.logger import get_logger
from src.utils.errors import ProjectManagementError, ValidationError


logger = get_logger(__name__)


@dataclass
class Project:
    """Project data structure"""
    id: str
    name: str
    description: str
    status: str
    start_date: datetime
    end_date: Optional[datetime]
    owner: str
    team_members: List[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class Task:
    """Task data structure"""
    id: str
    project_id: str
    title: str
    description: str
    status: str
    priority: str
    assignee: str
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime


@dataclass
class TeamMember:
    """Team member data structure"""
    id: str
    name: str
    email: str
    role: str
    skills: List[str]
    availability: float  # 0.0 to 1.0
    current_workload: float  # 0.0 to 1.0


class ProjectManagementTools:
    """Collection of tools for project management agents"""
    
    def __init__(self):
        self.projects: Dict[str, Project] = {}
        self.tasks: Dict[str, Task] = {}
        self.team_members: Dict[str, TeamMember] = {}
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize with sample data for testing"""
        # Sample team members
        self.team_members = {
            "user1": TeamMember(
                id="user1",
                name="Alice Johnson",
                email="alice@company.com",
                role="Project Manager",
                skills=["project_management", "agile", "scrum"],
                availability=0.8,
                current_workload=0.6
            ),
            "user2": TeamMember(
                id="user2",
                name="Bob Smith",
                email="bob@company.com",
                role="Developer",
                skills=["python", "javascript", "react"],
                availability=0.9,
                current_workload=0.4
            ),
            "user3": TeamMember(
                id="user3",
                name="Carol Davis",
                email="carol@company.com",
                role="Designer",
                skills=["ui_design", "ux_design", "figma"],
                availability=0.7,
                current_workload=0.5
            )
        }
    
    # Project Management Tools
    
    async def create_project(
        self,
        name: str,
        description: str,
        owner: str,
        team_members: List[str] = None,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """Create a new project"""
        try:
            project_id = f"proj_{len(self.projects) + 1}"
            
            # Parse dates
            start_dt = datetime.now() if not start_date else datetime.fromisoformat(start_date)
            end_dt = None if not end_date else datetime.fromisoformat(end_date)
            
            project = Project(
                id=project_id,
                name=name,
                description=description,
                status="planning",
                start_date=start_dt,
                end_date=end_dt,
                owner=owner,
                team_members=team_members or [],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.projects[project_id] = project
            
            logger.info(f"Created project: {project_id} - {name}")
            
            return {
                "success": True,
                "project_id": project_id,
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "status": project.status,
                    "owner": project.owner,
                    "team_members": project.team_members
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            raise ProjectManagementError(f"Failed to create project: {str(e)}")
    
    async def update_project(
        self,
        project_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing project"""
        try:
            if project_id not in self.projects:
                raise ValidationError(f"Project {project_id} not found")
            
            project = self.projects[project_id]
            
            # Update fields
            for key, value in updates.items():
                if hasattr(project, key):
                    setattr(project, key, value)
            
            project.updated_at = datetime.now()
            
            logger.info(f"Updated project: {project_id}")
            
            return {
                "success": True,
                "project_id": project_id,
                "updated_fields": list(updates.keys())
            }
            
        except Exception as e:
            logger.error(f"Failed to update project: {e}")
            raise ProjectManagementError(f"Failed to update project: {str(e)}")
    
    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project details"""
        try:
            if project_id not in self.projects:
                raise ValidationError(f"Project {project_id} not found")
            
            project = self.projects[project_id]
            
            return {
                "success": True,
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "status": project.status,
                    "start_date": project.start_date.isoformat(),
                    "end_date": project.end_date.isoformat() if project.end_date else None,
                    "owner": project.owner,
                    "team_members": project.team_members,
                    "created_at": project.created_at.isoformat(),
                    "updated_at": project.updated_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get project: {e}")
            raise ProjectManagementError(f"Failed to get project: {str(e)}")
    
    async def list_projects(self, owner: str = None) -> Dict[str, Any]:
        """List all projects or projects by owner"""
        try:
            projects = list(self.projects.values())
            
            if owner:
                projects = [p for p in projects if p.owner == owner]
            
            return {
                "success": True,
                "projects": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "description": p.description,
                        "status": p.status,
                        "owner": p.owner,
                        "team_members": p.team_members
                    }
                    for p in projects
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            raise ProjectManagementError(f"Failed to list projects: {str(e)}")
    
    # Task Management Tools
    
    async def create_task(
        self,
        project_id: str,
        title: str,
        description: str,
        assignee: str,
        priority: str = "medium",
        due_date: str = None
    ) -> Dict[str, Any]:
        """Create a new task"""
        try:
            if project_id not in self.projects:
                raise ValidationError(f"Project {project_id} not found")
            
            task_id = f"task_{len(self.tasks) + 1}"
            
            # Parse due date
            due_dt = None if not due_date else datetime.fromisoformat(due_date)
            
            task = Task(
                id=task_id,
                project_id=project_id,
                title=title,
                description=description,
                status="todo",
                priority=priority,
                assignee=assignee,
                due_date=due_dt,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.tasks[task_id] = task
            
            logger.info(f"Created task: {task_id} - {title}")
            
            return {
                "success": True,
                "task_id": task_id,
                "task": {
                    "id": task.id,
                    "project_id": task.project_id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "priority": task.priority,
                    "assignee": task.assignee,
                    "due_date": task.due_date.isoformat() if task.due_date else None
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise ProjectManagementError(f"Failed to create task: {str(e)}")
    
    async def update_task_status(
        self,
        task_id: str,
        status: str
    ) -> Dict[str, Any]:
        """Update task status"""
        try:
            if task_id not in self.tasks:
                raise ValidationError(f"Task {task_id} not found")
            
            task = self.tasks[task_id]
            task.status = status
            task.updated_at = datetime.now()
            
            logger.info(f"Updated task {task_id} status to {status}")
            
            return {
                "success": True,
                "task_id": task_id,
                "status": status
            }
            
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            raise ProjectManagementError(f"Failed to update task status: {str(e)}")
    
    async def assign_task(
        self,
        task_id: str,
        assignee: str
    ) -> Dict[str, Any]:
        """Assign task to team member"""
        try:
            if task_id not in self.tasks:
                raise ValidationError(f"Task {task_id} not found")
            
            if assignee not in self.team_members:
                raise ValidationError(f"Team member {assignee} not found")
            
            task = self.tasks[task_id]
            task.assignee = assignee
            task.updated_at = datetime.now()
            
            logger.info(f"Assigned task {task_id} to {assignee}")
            
            return {
                "success": True,
                "task_id": task_id,
                "assignee": assignee
            }
            
        except Exception as e:
            logger.error(f"Failed to assign task: {e}")
            raise ProjectManagementError(f"Failed to assign task: {str(e)}")
    
    async def get_project_tasks(self, project_id: str) -> Dict[str, Any]:
        """Get all tasks for a project"""
        try:
            project_tasks = [
                task for task in self.tasks.values()
                if task.project_id == project_id
            ]
            
            return {
                "success": True,
                "tasks": [
                    {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "status": task.status,
                        "priority": task.priority,
                        "assignee": task.assignee,
                        "due_date": task.due_date.isoformat() if task.due_date else None
                    }
                    for task in project_tasks
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get project tasks: {e}")
            raise ProjectManagementError(f"Failed to get project tasks: {str(e)}")
    
    # Team Management Tools
    
    async def get_team_members(self) -> Dict[str, Any]:
        """Get all team members"""
        try:
            return {
                "success": True,
                "team_members": [
                    {
                        "id": member.id,
                        "name": member.name,
                        "email": member.email,
                        "role": member.role,
                        "skills": member.skills,
                        "availability": member.availability,
                        "current_workload": member.current_workload
                    }
                    for member in self.team_members.values()
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get team members: {e}")
            raise ProjectManagementError(f"Failed to get team members: {str(e)}")
    
    async def get_team_member(self, member_id: str) -> Dict[str, Any]:
        """Get specific team member details"""
        try:
            if member_id not in self.team_members:
                raise ValidationError(f"Team member {member_id} not found")
            
            member = self.team_members[member_id]
            
            return {
                "success": True,
                "team_member": {
                    "id": member.id,
                    "name": member.name,
                    "email": member.email,
                    "role": member.role,
                    "skills": member.skills,
                    "availability": member.availability,
                    "current_workload": member.current_workload
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get team member: {e}")
            raise ProjectManagementError(f"Failed to get team member: {str(e)}")
    
    # Progress Tracking Tools
    
    async def get_project_progress(self, project_id: str) -> Dict[str, Any]:
        """Get project progress metrics"""
        try:
            if project_id not in self.projects:
                raise ValidationError(f"Project {project_id} not found")
            
            project_tasks = [
                task for task in self.tasks.values()
                if task.project_id == project_id
            ]
            
            total_tasks = len(project_tasks)
            completed_tasks = len([task for task in project_tasks if task.status == "completed"])
            in_progress_tasks = len([task for task in project_tasks if task.status == "in_progress"])
            
            progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            return {
                "success": True,
                "progress": {
                    "project_id": project_id,
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "in_progress_tasks": in_progress_tasks,
                    "progress_percentage": round(progress_percentage, 2),
                    "status_breakdown": {
                        "todo": len([task for task in project_tasks if task.status == "todo"]),
                        "in_progress": in_progress_tasks,
                        "completed": completed_tasks,
                        "blocked": len([task for task in project_tasks if task.status == "blocked"])
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get project progress: {e}")
            raise ProjectManagementError(f"Failed to get project progress: {str(e)}")
    
    # Risk Assessment Tools
    
    async def assess_project_risks(self, project_id: str) -> Dict[str, Any]:
        """Assess risks for a project"""
        try:
            if project_id not in self.projects:
                raise ValidationError(f"Project {project_id} not found")
            
            project = self.projects[project_id]
            project_tasks = [
                task for task in self.tasks.values()
                if task.project_id == project_id
            ]
            
            # Simple risk assessment based on project characteristics
            risks = []
            
            # Overdue tasks risk
            overdue_tasks = [
                task for task in project_tasks
                if task.due_date and task.due_date < datetime.now() and task.status != "completed"
            ]
            if overdue_tasks:
                risks.append({
                    "type": "schedule_risk",
                    "description": f"{len(overdue_tasks)} overdue tasks",
                    "severity": "high",
                    "probability": 0.8
                })
            
            # High priority tasks risk
            high_priority_tasks = [
                task for task in project_tasks
                if task.priority == "high" and task.status != "completed"
            ]
            if len(high_priority_tasks) > 3:
                risks.append({
                    "type": "resource_risk",
                    "description": "Too many high priority tasks",
                    "severity": "medium",
                    "probability": 0.6
                })
            
            # Team workload risk
            team_workload = sum(
                member.current_workload for member in self.team_members.values()
            ) / len(self.team_members) if self.team_members else 0
            
            if team_workload > 0.8:
                risks.append({
                    "type": "capacity_risk",
                    "description": "High team workload",
                    "severity": "medium",
                    "probability": 0.7
                })
            
            return {
                "success": True,
                "risks": risks,
                "risk_score": len(risks) * 0.3,  # Simple risk score
                "assessment_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to assess project risks: {e}")
            raise ProjectManagementError(f"Failed to assess project risks: {str(e)}")


# Global tools instance
pm_tools = ProjectManagementTools()


