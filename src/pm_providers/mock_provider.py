# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Mock PM Provider - Returns realistic mock data for demos and testing

This provider implements the BasePMProvider interface but returns
generated mock data instead of connecting to a real PM system.
Perfect for demos, presentations, and development.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date
import random
from uuid import uuid4

from .base import BasePMProvider
from .models import (
    PMUser, PMProject, PMTask, PMSprint, PMEpic, PMComponent, PMLabel,
    PMProviderConfig, PMStatusTransition
)

logger = logging.getLogger(__name__)


class MockPMProvider(BasePMProvider):
    """
    Mock PM Provider that returns realistic generated data.
    
    This provider implements all BasePMProvider methods but returns
    mock data instead of making real API calls. It maintains consistent
    data across calls within a session.
    """
    
    def __init__(self, config: PMProviderConfig):
        """Initialize mock provider with configuration"""
        super().__init__(config)
        self.provider_type = "mock"
        self._initialize_mock_data()
    
    def _initialize_mock_data(self):
        """Initialize consistent mock data for the session"""
        
        # Mock users
        self.mock_users = [
            PMUser(
                id="user-1",
                name="Alice Johnson",
                email="alice@example.com",
                avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=Alice"
            ),
            PMUser(
                id="user-2",
                name="Bob Smith",
                email="bob@example.com",
                avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=Bob"
            ),
            PMUser(
                id="user-3",
                name="Carol Williams",
                email="carol@example.com",
                avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=Carol"
            ),
            PMUser(
                id="user-4",
                name="David Brown",
                email="david@example.com",
                avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=David"
            ),
        ]
        
        # Mock statuses (match UI expectations)
        self.mock_statuses = [
            {"id": "todo", "name": "To Do", "category": "todo"},
            {"id": "in_progress", "name": "In Progress", "category": "in_progress"},
            {"id": "in_review", "name": "In Review", "category": "in_progress"},
            {"id": "done", "name": "Done", "category": "done"},
        ]
        
        # Mock priorities (match UI expectations)
        self.mock_priorities = [
            {"id": "low", "name": "Low", "color": "#3b82f6"},
            {"id": "medium", "name": "Medium", "color": "#f59e0b"},
            {"id": "high", "name": "High", "color": "#ef4444"},
            {"id": "critical", "name": "Critical", "color": "#7c3aed"},
        ]
        
        # Mock project
        self.mock_project = PMProject(
            id="demo",
            name="Demo Project",
            description="A demo project with realistic mock data for presentations and testing",
            created_at=datetime.now() - timedelta(days=90),
            updated_at=datetime.now()
        )
        
        # Mock sprints
        today = date.today()
        self.mock_sprints = [
            PMSprint(
                id="sprint-1",
                name="Sprint 1",
                project_id="demo",
                start_date=today - timedelta(days=42),
                end_date=today - timedelta(days=28),
                status="closed",
                goal="Complete user authentication and basic dashboard"
            ),
            PMSprint(
                id="sprint-2",
                name="Sprint 2",
                project_id="demo",
                start_date=today - timedelta(days=28),
                end_date=today - timedelta(days=14),
                status="closed",
                goal="Implement project management features"
            ),
            PMSprint(
                id="sprint-3",
                name="Sprint 3",
                project_id="demo",
                start_date=today - timedelta(days=14),
                end_date=today,
                status="active",
                goal="Add analytics and reporting capabilities"
            ),
            PMSprint(
                id="sprint-4",
                name="Sprint 4",
                project_id="demo",
                start_date=today,
                end_date=today + timedelta(days=14),
                status="future",
                goal="Performance optimization and bug fixes"
            ),
        ]
        
        # Mock epics
        self.mock_epics = [
            PMEpic(
                id="epic-1",
                name="User Management",
                description="Complete user management system with authentication and profiles",
                project_id="demo",
                status="done",
                created_at=datetime.now() - timedelta(days=80)
            ),
            PMEpic(
                id="epic-2",
                name="Project Management",
                description="Core project management features including tasks, sprints, and boards",
                project_id="demo",
                status="in_progress",
                created_at=datetime.now() - timedelta(days=60)
            ),
            PMEpic(
                id="epic-3",
                name="Analytics & Reporting",
                description="Advanced analytics, charts, and reporting capabilities",
                project_id="demo",
                status="todo",
                created_at=datetime.now() - timedelta(days=30)
            ),
        ]
        
        # Mock tasks
        self.mock_tasks = self._generate_mock_tasks()
    
    def _generate_mock_tasks(self) -> List[PMTask]:
        """Generate realistic mock tasks that align with the simplified PMTask model"""
        status_map = {
            "todo": "todo",
            "in_progress": "in_progress",
            "in_review": "in_review",
            "done": "done",
        }

        priority_sequence = ["medium", "high", "medium", "critical"]

        task_blueprints = [
            # sprint_id, epic_id, status, hours, assignee_id, title
            ("sprint-1", "epic-1", "done", 16, "user-1", "Implement user authentication"),
            ("sprint-1", "epic-1", "done", 12, "user-2", "Create login page UI"),
            ("sprint-1", "epic-1", "done", 10, "user-3", "Setup JWT token system"),
            ("sprint-1", "epic-1", "done", 14, "user-4", "Design dashboard layout"),
            ("sprint-2", "epic-2", "done", 20, "user-1", "Create project CRUD operations"),
            ("sprint-2", "epic-2", "done", 12, "user-2", "Implement task board view"),
            ("sprint-2", "epic-2", "done", 10, "user-3", "Add drag and drop functionality"),
            ("sprint-2", "epic-2", "done", 18, "user-4", "Setup sprint management"),
            ("sprint-3", "epic-3", "done", 10, "user-1", "Design analytics dashboard"),
            ("sprint-3", "epic-3", "done", 12, "user-2", "Implement burndown chart"),
            ("sprint-3", "epic-3", "in_review", 12, "user-3", "Create velocity chart"),
            ("sprint-3", "epic-3", "in_progress", 8, "user-4", "Add CFD visualization"),
            ("sprint-3", "epic-3", "todo", 8, "user-1", "Implement cycle time chart"),
            ("sprint-3", "epic-3", "todo", 12, "user-2", "Create sprint report view"),
            (None, "epic-3", "todo", 20, None, "Add export to PDF feature"),
            (None, "epic-2", "todo", 16, None, "Implement email notifications"),
            (None, "epic-2", "todo", 18, None, "Create mobile responsive views"),
            (None, None, "todo", 10, None, "Add dark mode support"),
        ]

        tasks: List[PMTask] = []
        now = datetime.now()

        for index, (sprint_id, epic_id, status_id, estimated_hours, assignee_id, title) in enumerate(task_blueprints, start=1):
            created_at = now - timedelta(days=60 - index * 2)
            updated_at = created_at + timedelta(days=random.randint(1, 10))
            completed_at = None
            if status_id == "done":
                completed_at = updated_at + timedelta(days=1)

            priority = priority_sequence[index % len(priority_sequence)]

            task = PMTask(
                id=f"task-{index}",
                title=title,
                description=f"Detailed description for {title}",
                status=status_map.get(status_id, status_id),
                priority=priority,
                project_id="demo",
                parent_task_id=None,
                epic_id=epic_id,
                assignee_id=assignee_id,
                component_ids=None,
                label_ids=None,
                sprint_id=sprint_id,
                estimated_hours=float(estimated_hours),
                actual_hours=None,
                start_date=None,
                due_date=None,
                created_at=created_at,
                updated_at=updated_at,
                completed_at=completed_at,
                raw_data={"key": f"DEMO-{index}"}
            )
            tasks.append(task)

        return tasks
    
    # ==================== Project Operations ====================
    
    async def list_projects(self) -> List[PMProject]:
        """List all projects"""
        logger.info("[MockProvider] Listing projects")
        return [self.mock_project]
    
    async def get_project(self, project_id: str) -> Optional[PMProject]:
        """Get a single project by ID"""
        logger.info(f"[MockProvider] Getting project: {project_id}")
        if project_id == "demo":
            return self.mock_project
        return None
    
    async def create_project(self, project: PMProject) -> PMProject:
        """Create a new project"""
        logger.info(f"[MockProvider] Creating project: {project.name}")
        project.id = str(uuid4())
        return project
    
    async def update_project(self, project_id: str, updates: Dict[str, Any]) -> PMProject:
        """Update an existing project"""
        logger.info(f"[MockProvider] Updating project: {project_id}")
        # Update mock project
        for key, value in updates.items():
            if hasattr(self.mock_project, key):
                setattr(self.mock_project, key, value)
        return self.mock_project
    
    async def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        logger.info(f"[MockProvider] Deleting project: {project_id}")
        return True
    
    # ==================== Task Operations ====================
    
    async def list_tasks(self, project_id: Optional[str] = None, assignee_id: Optional[str] = None) -> List[PMTask]:
        """List all tasks, optionally filtered by project and/or assignee"""
        logger.info(f"[MockProvider] Listing tasks (project={project_id}, assignee={assignee_id})")
        tasks = self.mock_tasks
        
        if project_id:
            tasks = [t for t in tasks if t.project_id == project_id]
        
        if assignee_id:
            tasks = [t for t in tasks if t.assignee_id == assignee_id]
        
        return tasks
    
    async def get_task(self, task_id: str) -> Optional[PMTask]:
        """Get a single task by ID"""
        logger.info(f"[MockProvider] Getting task: {task_id}")
        return next((t for t in self.mock_tasks if t.id == task_id), None)
    
    async def create_task(self, task: PMTask) -> PMTask:
        """Create a new task"""
        logger.info(f"[MockProvider] Creating task: {task.title}")
        task.id = f"task-{len(self.mock_tasks) + 1}"
        task.created_at = datetime.now()
        task.updated_at = datetime.now()
        self.mock_tasks.append(task)
        return task
    
    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> PMTask:
        """Update an existing task"""
        logger.info(f"[MockProvider] Updating task: {task_id}")
        task = next((t for t in self.mock_tasks if t.id == task_id), None)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        # Update task fields
        for key, value in updates.items():
            if key == "status" and isinstance(value, str):
                task.status = value
            elif key == "assignee_id":
                task.assignee_id = value
            elif hasattr(task, key):
                setattr(task, key, value)
        
        task.updated_at = datetime.now()
        return task
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        logger.info(f"[MockProvider] Deleting task: {task_id}")
        self.mock_tasks = [t for t in self.mock_tasks if t.id != task_id]
        return True
    
    # ==================== Sprint Operations ====================
    
    async def list_sprints(
        self, project_id: Optional[str] = None, state: Optional[str] = None
    ) -> List[PMSprint]:
        """List all sprints, optionally filtered by project"""
        logger.info(f"[MockProvider] Listing sprints (project={project_id}, state={state})")
        sprints = self.mock_sprints
        
        if project_id:
            sprints = [s for s in sprints if s.project_id == project_id]
        
        if state:
            sprints = [s for s in sprints if s.status == state]
        
        return sprints
    
    async def get_sprint(self, sprint_id: str) -> Optional[PMSprint]:
        """Get a single sprint by ID"""
        logger.info(f"[MockProvider] Getting sprint: {sprint_id}")
        return next((s for s in self.mock_sprints if s.id == sprint_id), None)
    
    async def create_sprint(self, sprint: PMSprint) -> PMSprint:
        """Create a new sprint"""
        logger.info(f"[MockProvider] Creating sprint: {sprint.name}")
        sprint.id = f"sprint-{len(self.mock_sprints) + 1}"
        self.mock_sprints.append(sprint)
        return sprint
    
    async def update_sprint(self, sprint_id: str, updates: Dict[str, Any]) -> PMSprint:
        """Update an existing sprint"""
        logger.info(f"[MockProvider] Updating sprint: {sprint_id}")
        sprint = next((s for s in self.mock_sprints if s.id == sprint_id), None)
        if not sprint:
            raise ValueError(f"Sprint not found: {sprint_id}")
        
        for key, value in updates.items():
            if hasattr(sprint, key):
                setattr(sprint, key, value)
        
        return sprint
    
    async def delete_sprint(self, sprint_id: str) -> bool:
        """Delete a sprint"""
        logger.info(f"[MockProvider] Deleting sprint: {sprint_id}")
        self.mock_sprints = [s for s in self.mock_sprints if s.id != sprint_id]
        return True
    
    # ==================== Epic Operations ====================
    
    async def list_epics(self, project_id: Optional[str] = None) -> List[PMEpic]:
        """List all epics, optionally filtered by project"""
        logger.info(f"[MockProvider] Listing epics (project={project_id})")
        epics = self.mock_epics
        
        if project_id:
            epics = [e for e in epics if e.project_id == project_id]
        
        return epics
    
    async def get_epic(self, epic_id: str) -> Optional[PMEpic]:
        """Get a single epic by ID"""
        logger.info(f"[MockProvider] Getting epic: {epic_id}")
        return next((e for e in self.mock_epics if e.id == epic_id), None)
    
    async def create_epic(self, epic: PMEpic) -> PMEpic:
        """Create a new epic"""
        logger.info(f"[MockProvider] Creating epic: {epic.name}")
        epic.id = f"epic-{len(self.mock_epics) + 1}"
        self.mock_epics.append(epic)
        return epic
    
    async def update_epic(self, epic_id: str, updates: Dict[str, Any]) -> PMEpic:
        """Update an existing epic"""
        logger.info(f"[MockProvider] Updating epic: {epic_id}")
        epic = next((e for e in self.mock_epics if e.id == epic_id), None)
        if not epic:
            raise ValueError(f"Epic not found: {epic_id}")
        
        for key, value in updates.items():
            if hasattr(epic, key):
                setattr(epic, key, value)
        
        return epic
    
    async def delete_epic(self, epic_id: str) -> bool:
        """Delete an epic"""
        logger.info(f"[MockProvider] Deleting epic: {epic_id}")
        self.mock_epics = [e for e in self.mock_epics if e.id != epic_id]
        return True
    
    # ==================== User Operations ====================
    
    async def list_users(self, project_id: Optional[str] = None) -> List[PMUser]:
        """List all users, optionally filtered by project"""
        logger.info(f"[MockProvider] Listing users (project={project_id})")
        return self.mock_users
    
    async def get_user(self, user_id: str) -> Optional[PMUser]:
        """Get a single user by ID"""
        logger.info(f"[MockProvider] Getting user: {user_id}")
        return next((u for u in self.mock_users if u.id == user_id), None)
    
    async def get_current_user(self) -> PMUser:
        """Get the currently authenticated user"""
        logger.info("[MockProvider] Getting current user")
        return self.mock_users[0]  # Alice is the current user
    
    # ==================== Status Operations ====================
    
    async def list_statuses(self, project_id: Optional[str] = None, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all statuses, optionally filtered by project"""
        logger.info(f"[MockProvider] Listing statuses (project={project_id})")
        return self.mock_statuses
    
    async def get_status_transitions(self, task_id: str) -> List[PMStatusTransition]:
        """Get available status transitions for a task"""
        logger.info(f"[MockProvider] Getting status transitions for task: {task_id}")
        transitions: List[PMStatusTransition] = []
        for source in self.mock_statuses:
            for target in self.mock_statuses:
                if source["id"] == target["id"]:
                    continue
                transitions.append(
                    PMStatusTransition(
                        from_status=source["id"],
                        to_status=target["id"],
                        name=f"Move to {target['name']}"
                    )
                )
        return transitions
    
    # ==================== Priority Operations ====================
    
    async def list_priorities(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all priorities"""
        logger.info("[MockProvider] Listing priorities")
        return self.mock_priorities
    
    # ==================== Component Operations ====================
    
    async def list_components(self, project_id: str) -> List[PMComponent]:
        """List all components for a project"""
        logger.info(f"[MockProvider] Listing components (project={project_id})")
        return []  # No components in mock data
    
    # ==================== Label Operations ====================
    
    async def list_labels(self, project_id: Optional[str] = None) -> List[PMLabel]:
        """List all labels, optionally filtered by project"""
        logger.info(f"[MockProvider] Listing labels (project={project_id})")
        return []  # No labels in mock data

    async def get_label(self, label_id: str) -> Optional[PMLabel]:
        logger.info(f"[MockProvider] Getting label: {label_id}")
        return next((label for label in [] if getattr(label, "id", None) == label_id), None)

    async def create_label(self, label: PMLabel) -> PMLabel:
        logger.info(f"[MockProvider] Creating label: {label.name}")
        label.id = label.id or str(uuid4())
        return label

    async def update_label(self, label_id: str, updates: Dict[str, Any]) -> PMLabel:
        logger.info(f"[MockProvider] Updating label: {label_id}")
        label = await self.get_label(label_id)
        if not label:
            raise ValueError(f"Label not found: {label_id}")
        for field, value in updates.items():
            if hasattr(label, field):
                setattr(label, field, value)
        return label

    async def delete_label(self, label_id: str) -> bool:
        logger.info(f"[MockProvider] Deleting label: {label_id}")
        return True

    # ==================== Comment Operations ====================
    
    async def list_comments(self, task_id: str) -> List[Dict[str, Any]]:
        """List all comments for a task"""
        logger.info(f"[MockProvider] Listing comments for task: {task_id}")
        return []  # No comments in mock data
    
    async def add_comment(self, task_id: str, body: str) -> Dict[str, Any]:
        """Add a comment to a task"""
        logger.info(f"[MockProvider] Adding comment to task: {task_id}")
        return {
            "id": str(uuid4()),
            "body": body,
            "author": {
                "id": self.mock_users[0].id,
                "name": self.mock_users[0].name,
                "email": self.mock_users[0].email,
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

    async def health_check(self) -> bool:
        logger.info("[MockProvider] Performing health check")
        return True

