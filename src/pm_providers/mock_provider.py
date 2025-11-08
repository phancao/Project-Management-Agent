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
    PMProviderConfig, PMStatus, PMPriority, PMStatusTransition, PMComment
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
        
        # Mock statuses
        self.mock_statuses = [
            PMStatus(id="1", name="To Do", category="todo"),
            PMStatus(id="2", name="In Progress", category="in_progress"),
            PMStatus(id="3", name="In Review", category="in_progress"),
            PMStatus(id="4", name="Done", category="done"),
        ]
        
        # Mock priorities
        self.mock_priorities = [
            PMPriority(id="1", name="Low"),
            PMPriority(id="2", name="Medium"),
            PMPriority(id="3", name="High"),
            PMPriority(id="4", name="Critical"),
        ]
        
        # Mock project
        self.mock_project = PMProject(
            id="demo",
            name="Demo Project",
            key="DEMO",
            description="A demo project with realistic mock data for presentations and testing",
            lead=self.mock_users[0],
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
                key="DEMO-EPIC-1",
                name="User Management",
                description="Complete user management system with authentication and profiles",
                project_id="demo",
                status=self.mock_statuses[3],  # Done
                created_at=datetime.now() - timedelta(days=80)
            ),
            PMEpic(
                id="epic-2",
                key="DEMO-EPIC-2",
                name="Project Management",
                description="Core project management features including tasks, sprints, and boards",
                project_id="demo",
                status=self.mock_statuses[1],  # In Progress
                created_at=datetime.now() - timedelta(days=60)
            ),
            PMEpic(
                id="epic-3",
                key="DEMO-EPIC-3",
                name="Analytics & Reporting",
                description="Advanced analytics, charts, and reporting capabilities",
                project_id="demo",
                status=self.mock_statuses[0],  # To Do
                created_at=datetime.now() - timedelta(days=30)
            ),
        ]
        
        # Mock tasks
        self.mock_tasks = self._generate_mock_tasks()
    
    def _generate_mock_tasks(self) -> List[PMTask]:
        """Generate realistic mock tasks"""
        tasks = []
        task_templates = [
            # Sprint 1 (Closed) - All done
            ("DEMO-1", "Implement user authentication", "epic-1", "sprint-1", "4", 8, self.mock_users[0]),
            ("DEMO-2", "Create login page UI", "epic-1", "sprint-1", "4", 5, self.mock_users[1]),
            ("DEMO-3", "Setup JWT token system", "epic-1", "sprint-1", "4", 5, self.mock_users[2]),
            ("DEMO-4", "Design dashboard layout", "epic-1", "sprint-1", "4", 8, self.mock_users[3]),
            
            # Sprint 2 (Closed) - All done
            ("DEMO-5", "Create project CRUD operations", "epic-2", "sprint-2", "4", 13, self.mock_users[0]),
            ("DEMO-6", "Implement task board view", "epic-2", "sprint-2", "4", 8, self.mock_users[1]),
            ("DEMO-7", "Add drag and drop functionality", "epic-2", "sprint-2", "4", 8, self.mock_users[2]),
            ("DEMO-8", "Setup sprint management", "epic-2", "sprint-2", "4", 13, self.mock_users[3]),
            
            # Sprint 3 (Active) - Mixed statuses
            ("DEMO-9", "Design analytics dashboard", "epic-3", "sprint-3", "4", 5, self.mock_users[0]),
            ("DEMO-10", "Implement burndown chart", "epic-3", "sprint-3", "4", 8, self.mock_users[1]),
            ("DEMO-11", "Create velocity chart", "epic-3", "sprint-3", "3", 8, self.mock_users[2]),
            ("DEMO-12", "Add CFD visualization", "epic-3", "sprint-3", "2", 5, self.mock_users[3]),
            ("DEMO-13", "Implement cycle time chart", "epic-3", "sprint-3", "1", 5, self.mock_users[0]),
            ("DEMO-14", "Create sprint report view", "epic-3", "sprint-3", "1", 8, self.mock_users[1]),
            
            # Backlog - No sprint
            ("DEMO-15", "Add export to PDF feature", "epic-3", None, "1", 13, None),
            ("DEMO-16", "Implement email notifications", "epic-2", None, "1", 8, None),
            ("DEMO-17", "Create mobile responsive views", "epic-2", None, "1", 13, None),
            ("DEMO-18", "Add dark mode support", None, None, "1", 5, None),
        ]
        
        for i, (key, title, epic_id, sprint_id, status_id, story_points, assignee) in enumerate(task_templates, 1):
            status = next(s for s in self.mock_statuses if s.id == status_id)
            epic = next((e for e in self.mock_epics if e.id == epic_id), None) if epic_id else None
            
            # Calculate dates based on sprint and status
            created_date = datetime.now() - timedelta(days=60 - i * 2)
            updated_date = datetime.now() - timedelta(days=random.randint(0, 10))
            
            # If task is done, set completion date
            completion_date = None
            if status.category == "done":
                completion_date = created_date + timedelta(days=random.randint(3, 10))
            
            task = PMTask(
                id=f"task-{i}",
                key=key,
                title=title,
                description=f"Detailed description for {title}",
                project_id="demo",
                status=status,
                priority=self.mock_priorities[random.randint(0, 3)],
                assignee=assignee,
                reporter=self.mock_users[0],
                epic=epic,
                sprint_id=sprint_id,
                story_points=story_points,
                created_at=created_date,
                updated_at=updated_date,
                completion_date=completion_date,
                labels=[],
                components=[]
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
            tasks = [t for t in tasks if t.assignee and t.assignee.id == assignee_id]
        
        return tasks
    
    async def get_task(self, task_id: str) -> Optional[PMTask]:
        """Get a single task by ID"""
        logger.info(f"[MockProvider] Getting task: {task_id}")
        return next((t for t in self.mock_tasks if t.id == task_id), None)
    
    async def create_task(self, task: PMTask) -> PMTask:
        """Create a new task"""
        logger.info(f"[MockProvider] Creating task: {task.title}")
        task.id = f"task-{len(self.mock_tasks) + 1}"
        task.key = f"DEMO-{len(self.mock_tasks) + 1}"
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
                # Find status by name or ID
                status = next((s for s in self.mock_statuses if s.name == value or s.id == value), None)
                if status:
                    task.status = status
            elif key == "assignee_id" and value:
                # Find user by ID
                user = next((u for u in self.mock_users if u.id == value), None)
                if user:
                    task.assignee = user
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
        epic.key = f"DEMO-EPIC-{len(self.mock_epics) + 1}"
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
    
    async def list_statuses(self, project_id: Optional[str] = None) -> List[PMStatus]:
        """List all statuses, optionally filtered by project"""
        logger.info(f"[MockProvider] Listing statuses (project={project_id})")
        return self.mock_statuses
    
    async def get_status_transitions(self, task_id: str) -> List[PMStatusTransition]:
        """Get available status transitions for a task"""
        logger.info(f"[MockProvider] Getting status transitions for task: {task_id}")
        # Allow all transitions in mock mode
        transitions = []
        for status in self.mock_statuses:
            transitions.append(PMStatusTransition(
                id=status.id,
                name=status.name,
                to_status=status
            ))
        return transitions
    
    # ==================== Priority Operations ====================
    
    async def list_priorities(self) -> List[PMPriority]:
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
    
    # ==================== Comment Operations ====================
    
    async def list_comments(self, task_id: str) -> List[PMComment]:
        """List all comments for a task"""
        logger.info(f"[MockProvider] Listing comments for task: {task_id}")
        return []  # No comments in mock data
    
    async def add_comment(self, task_id: str, body: str) -> PMComment:
        """Add a comment to a task"""
        logger.info(f"[MockProvider] Adding comment to task: {task_id}")
        return PMComment(
            id=str(uuid4()),
            body=body,
            author=self.mock_users[0],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

