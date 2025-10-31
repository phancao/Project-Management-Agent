"""
Internal PM Provider

Uses our own database as the PM backend.
This wraps the existing database CRUD operations.
"""
from typing import List, Optional, Dict, Any
from datetime import date, datetime

from .base import BasePMProvider
from .models import PMUser, PMProject, PMTask, PMSprint, PMProviderConfig
from database import crud, orm_models
from sqlalchemy.orm import Session


class InternalPMProvider(BasePMProvider):
    """
    Internal database as PM provider
    
    Uses our existing PostgreSQL database with standard CRUD operations.
    This provides a seamless abstraction layer for our existing data.
    """
    
    def __init__(self, config: PMProviderConfig, db_session: Session):
        super().__init__(config)
        self.db_session = db_session
    
    # ==================== Project Operations ====================
    
    async def list_projects(self) -> List[PMProject]:
        """List all projects from internal database"""
        projects = crud.get_projects(self.db_session, limit=1000)
        return [self._project_to_pm(p) for p in projects]
    
    async def get_project(self, project_id: str) -> Optional[PMProject]:
        """Get a single project by ID"""
        from uuid import UUID
        project = crud.get_project(self.db_session, UUID(project_id))
        if not project:
            return None
        return self._project_to_pm(project)
    
    async def create_project(self, project: PMProject) -> PMProject:
        """Create a new project"""
        from uuid import UUID
        created = crud.create_project(
            self.db_session,
            name=project.name,
            description=project.description,
            created_by=UUID(project.owner_id) if project.owner_id else UUID("f430f348-d65f-427f-9379-3d0f163393d1"),
            domain=None,
            priority=project.priority or "medium",
            timeline_weeks=None,
            budget=None
        )
        return self._project_to_pm(created)
    
    async def update_project(self, project_id: str, updates: Dict[str, Any]) -> PMProject:
        """Update an existing project"""
        from uuid import UUID
        updated = crud.update_project(self.db_session, UUID(project_id), **updates)
        if not updated:
            raise ValueError(f"Project {project_id} not found")
        return self._project_to_pm(updated)
    
    async def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        from uuid import UUID
        return crud.delete_project(self.db_session, UUID(project_id))
    
    # ==================== Task Operations ====================
    
    async def list_tasks(self, project_id: Optional[str] = None) -> List[PMTask]:
        """List all tasks from internal database"""
        from uuid import UUID
        if project_id:
            tasks = crud.get_tasks_by_project(self.db_session, UUID(project_id))
        else:
            # Get all tasks - we need to query all projects first
            projects = crud.get_projects(self.db_session, limit=1000)
            all_tasks = []
            for project in projects:
                all_tasks.extend(crud.get_tasks_by_project(self.db_session, project.id))
            tasks = all_tasks
        return [self._task_to_pm(t) for t in tasks]
    
    async def get_task(self, task_id: str) -> Optional[PMTask]:
        """Get a single task by ID"""
        from uuid import UUID
        task = crud.get_task(self.db_session, UUID(task_id))
        if not task:
            return None
        return self._task_to_pm(task)
    
    async def create_task(self, task: PMTask) -> PMTask:
        """Create a new task"""
        from uuid import UUID
        created = crud.create_task(
            self.db_session,
            project_id=UUID(task.project_id) if task.project_id else None,
            title=task.title,
            description=task.description,
            priority=task.priority or "medium",
            estimated_hours=task.estimated_hours,
            due_date=task.due_date,
            assigned_to=UUID(task.assignee_id) if task.assignee_id else None,
            parent_task_id=UUID(task.parent_task_id) if task.parent_task_id else None
        )
        return self._task_to_pm(created)
    
    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> PMTask:
        """Update an existing task"""
        from uuid import UUID
        # Map PM field names to internal field names
        mapped_updates = {}
        field_mapping = {
            "title": "title",
            "description": "description",
            "status": "status",
            "priority": "priority",
            "estimated_hours": "estimated_hours",
            "due_date": "due_date",
            "assignee_id": "assigned_to"
        }
        for key, value in updates.items():
            if key in field_mapping and value is not None:
                if key == "assignee_id":
                    mapped_updates[field_mapping[key]] = UUID(value)
                else:
                    mapped_updates[field_mapping[key]] = value
        
        updated = crud.update_task(self.db_session, UUID(task_id), **mapped_updates)
        if not updated:
            raise ValueError(f"Task {task_id} not found")
        return self._task_to_pm(updated)
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        from uuid import UUID
        return crud.delete_task(self.db_session, UUID(task_id))
    
    # ==================== Sprint Operations ====================
    
    async def list_sprints(self, project_id: Optional[str] = None) -> List[PMSprint]:
        """List all sprints from internal database"""
        from uuid import UUID
        from sqlalchemy import select
        query = select(orm_models.Sprint)
        if project_id:
            query = query.where(orm_models.Sprint.project_id == UUID(project_id))
        sprints = self.db_session.execute(query).scalars().all()
        return [self._sprint_to_pm(s) for s in sprints]
    
    async def get_sprint(self, sprint_id: str) -> Optional[PMSprint]:
        """Get a single sprint by ID"""
        from uuid import UUID
        sprint = crud.get_sprint(self.db_session, UUID(sprint_id))
        if not sprint:
            return None
        return self._sprint_to_pm(sprint)
    
    async def create_sprint(self, sprint: PMSprint) -> PMSprint:
        """Create a new sprint"""
        from uuid import UUID
        from src.handlers.sprint_planner import Sprint as SprintDataclass
        
        # Create sprint using existing logic
        sprint_data = SprintDataclass(
            name=sprint.name,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            capacity_hours=sprint.capacity_hours,
            duration_weeks=None,
            duration_days=None
        )
        
        # We need to use the SprintPlanner to create sprints properly
        # For now, just create a basic sprint record
        db_sprint = orm_models.Sprint(
            project_id=UUID(sprint.project_id),
            name=sprint.name,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            capacity_hours=sprint.capacity_hours,
            status=sprint.status or "planned"
        )
        self.db_session.add(db_sprint)
        self.db_session.commit()
        self.db_session.refresh(db_sprint)
        return self._sprint_to_pm(db_sprint)
    
    async def update_sprint(self, sprint_id: str, updates: Dict[str, Any]) -> PMSprint:
        """Update an existing sprint"""
        from uuid import UUID
        updated = crud.update_sprint(self.db_session, UUID(sprint_id), **updates)
        if not updated:
            raise ValueError(f"Sprint {sprint_id} not found")
        return self._sprint_to_pm(updated)
    
    async def delete_sprint(self, sprint_id: str) -> bool:
        """Delete a sprint"""
        from uuid import UUID
        sprint = self.db_session.get(orm_models.Sprint, UUID(sprint_id))
        if sprint:
            self.db_session.delete(sprint)
            self.db_session.commit()
            return True
        return False
    
    # ==================== User Operations ====================
    
    async def list_users(self, project_id: Optional[str] = None) -> List[PMUser]:
        """List all users"""
        users = crud.get_users(self.db_session, limit=1000)
        return [self._user_to_pm(u) for u in users]
    
    async def get_user(self, user_id: str) -> Optional[PMUser]:
        """Get a single user by ID"""
        from uuid import UUID
        user = crud.get_user(self.db_session, UUID(user_id))
        if not user:
            return None
        return self._user_to_pm(user)
    
    # ==================== Health Check ====================
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            # Simple query to test connection
            self.db_session.execute("SELECT 1")
            return True
        except:
            return False
    
    # ==================== Conversion Methods ====================
    
    def _project_to_pm(self, proj) -> PMProject:
        """Convert internal Project to PMProject"""
        return PMProject(
            id=str(proj.id),
            name=proj.name,
            description=proj.description,
            status=proj.status,
            priority=proj.priority,
            created_at=proj.created_at,
            updated_at=proj.updated_at,
            owner_id=str(proj.created_by)
        )
    
    def _task_to_pm(self, task) -> PMTask:
        """Convert internal Task to PMTask"""
        return PMTask(
            id=str(task.id),
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            project_id=str(task.project_id),
            parent_task_id=str(task.parent_task_id) if task.parent_task_id else None,
            assignee_id=str(task.assigned_to) if task.assigned_to else None,
            estimated_hours=task.estimated_hours,
            due_date=task.due_date,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at
        )
    
    def _sprint_to_pm(self, sprint) -> PMSprint:
        """Convert internal Sprint to PMSprint"""
        return PMSprint(
            id=str(sprint.id),
            name=sprint.name,
            project_id=str(sprint.project_id),
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            status=sprint.status,
            capacity_hours=sprint.capacity_hours,
            planned_hours=sprint.planned_hours,
            created_at=sprint.created_at,
            updated_at=sprint.updated_at
        )
    
    def _user_to_pm(self, user) -> PMUser:
        """Convert internal User to PMUser"""
        return PMUser(
            id=str(user.id),
            name=user.name,
            email=user.email
        )

