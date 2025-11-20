"""
Mock PM Provider with persistent dataset generated via the WBS LLM.
"""

from __future__ import annotations

import logging
import random
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from database.connection import SessionLocal, get_db_engine
from database.orm_models import Base, MockEpic, MockProject, MockSprint, MockTask, MockUser
# Optional imports - only used if available
try:
    from backend.handlers import WBSGenerator
    HAS_WBS_GENERATOR = True
except ImportError:
    HAS_WBS_GENERATOR = False

try:
    from backend.llms.llm import get_llm_by_type
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

from .base import BasePMProvider
from .models import (
    PMComponent,
    PMEpic,
    PMLabel,
    PMProject,
    PMProviderConfig,
    PMStatusTransition,
    PMSprint,
    PMTask,
    PMUser,
)

logger = logging.getLogger(__name__)


class MockPMProvider(BasePMProvider):
    """Projects, sprints, epics, and tasks backed by the mock database."""

    PROJECT_ID = "demo"
    PROJECT_NAME = "Mock Project (Demo Data)"
    PROJECT_DESCRIPTION = (
        "Demo dataset used across backlog, analytics, timeline, and team views."
    )

    DEFAULT_USERS: List[Dict[str, str]] = [
        {
            "id": "mock-user-1",
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "role": "Product Manager",
            "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Alice",
        },
        {
            "id": "mock-user-2",
            "name": "Bob Smith",
            "email": "bob@example.com",
            "role": "Lead Engineer",
            "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Bob",
        },
        {
            "id": "mock-user-3",
            "name": "Carol Williams",
            "email": "carol@example.com",
            "role": "UX Designer",
            "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Carol",
        },
        {
            "id": "mock-user-4",
            "name": "David Brown",
            "email": "david@example.com",
            "role": "QA Engineer",
            "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=David",
        },
    ]

    _schema_initialized: bool = False

    def __init__(self, config: PMProviderConfig):
        super().__init__(config)
        self.provider_type = "mock"
        self._session_factory = SessionLocal
        self._ensure_schema()
        self._ensure_seed_data()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _session(self) -> Session:
        return self._session_factory()

    def _ensure_schema(self) -> None:
        """Ensure required tables exist before accessing them."""
        if getattr(self.__class__, "_schema_initialized", False):
            return
        engine = get_db_engine()
        Base.metadata.create_all(
            bind=engine,
            tables=[
                MockProject.__table__,
                MockUser.__table__,
                MockSprint.__table__,
                MockEpic.__table__,
                MockTask.__table__,
            ],
        )
        self.__class__._schema_initialized = True

    def _normalize_project_id(self, project_id: Optional[str]) -> str:
        if not project_id:
            return self.PROJECT_ID
        return project_id.split(":", 1)[-1]

    def _ensure_seed_data(self) -> None:
        with self._session() as session:
            project = session.get(MockProject, self.PROJECT_ID)
            if not project:
                project = MockProject(
                    id=self.PROJECT_ID,
                    name=self.PROJECT_NAME,
                    description=self.PROJECT_DESCRIPTION,
                )
                session.add(project)

            for user in self.DEFAULT_USERS:
                if not session.get(MockUser, user["id"]):
                    session.add(MockUser(**user))

            session.commit()

            has_tasks = (
                session.query(MockTask.id)
                .filter(MockTask.project_id == self.PROJECT_ID)
                .first()
            )
            if not has_tasks:
                self._seed_template_dataset(session)

    def _seed_template_dataset(self, session: Session) -> None:
        """Populate database with the legacy static dataset."""
        today = date.today()

        session.query(MockTask).filter_by(project_id=self.PROJECT_ID).delete()
        session.query(MockEpic).filter_by(project_id=self.PROJECT_ID).delete()
        session.query(MockSprint).filter_by(project_id=self.PROJECT_ID).delete()
        session.commit()

        sprints_data = [
            {
                "id": "sprint-1",
                "name": "Sprint 1",
                "status": "closed",
                "start": today - timedelta(days=42),
                "end": today - timedelta(days=28),
                "goal": "Complete user authentication and basic dashboard",
            },
            {
                "id": "sprint-2",
                "name": "Sprint 2",
                "status": "closed",
                "start": today - timedelta(days=28),
                "end": today - timedelta(days=14),
                "goal": "Implement project management features",
            },
            {
                "id": "sprint-3",
                "name": "Sprint 3",
                "status": "active",
                "start": today - timedelta(days=14),
                "end": today,
                "goal": "Add analytics and reporting capabilities",
            },
            {
                "id": "sprint-4",
                "name": "Sprint 4",
                "status": "future",
                "start": today,
                "end": today + timedelta(days=14),
                "goal": "Performance optimization and bug fixes",
            },
        ]

        for sprint in sprints_data:
            session.add(
                MockSprint(
                    id=sprint["id"],
                    project_id=self.PROJECT_ID,
                    name=sprint["name"],
                    status=sprint["status"],
                    start_date=sprint["start"],
                    end_date=sprint["end"],
                    goal=sprint["goal"],
                )
            )

        epics_data = [
            {
                "id": "epic-1",
                "name": "User Management",
                "description": "Complete user management system with authentication and profiles",
                "status": "done",
            },
            {
                "id": "epic-2",
                "name": "Project Management",
                "description": "Core PM features including tasks, sprints, and boards",
                "status": "in_progress",
            },
            {
                "id": "epic-3",
                "name": "Analytics & Reporting",
                "description": "Advanced analytics, charts, and reporting capabilities",
                "status": "todo",
            },
        ]

        for epic in epics_data:
            session.add(
                MockEpic(
                    id=epic["id"],
                    project_id=self.PROJECT_ID,
                    name=epic["name"],
                    description=epic["description"],
                    status=epic["status"],
                )
            )

        def make_task(
            task_id: str,
            title: str,
            description: str,
            status: str,
            priority: str,
            sprint_id: Optional[str],
            epic_id: Optional[str],
            assignee_id: Optional[str],
            estimated_hours: float,
            start_offset: int = 0,
            duration: int = 5,
        ) -> MockTask:
            sprint = next((s for s in sprints_data if s["id"] == sprint_id), None)
            start_date = (
                sprint["start"] + timedelta(days=start_offset) if sprint else today
            )
            due_date = (
                min(start_date + timedelta(days=duration), sprint["end"])
                if sprint
                else start_date + timedelta(days=duration)
            )
            return MockTask(
                id=task_id,
                project_id=self.PROJECT_ID,
                sprint_id=sprint_id,
                epic_id=epic_id,
                assignee_id=assignee_id,
                title=title,
                description=description,
                status=status,
                priority=priority,
                estimated_hours=estimated_hours,
                start_date=start_date,
                due_date=due_date,
            )

        session.add_all(
            [
                make_task(
                    "task-1",
                    "Implement user authentication",
                    "Implement user registration and login flow using JWT",
                    "done",
                    "high",
                    "sprint-1",
                    "epic-1",
                    "mock-user-1",
                    16,
                ),
                make_task(
                    "task-2",
                    "Create login page UI",
                    "Design and implement responsive login and signup UI",
                    "done",
                    "medium",
                    "sprint-1",
                    "epic-1",
                    "mock-user-2",
                    12,
                ),
                make_task(
                    "task-3",
                    "Setup JWT token system",
                    "Configure backend JWT authentication and refresh tokens",
                    "done",
                    "high",
                    "sprint-1",
                    "epic-1",
                    "mock-user-3",
                    10,
                ),
                make_task(
                    "task-4",
                    "Design dashboard layout",
                    "Create dashboard layout with key metrics and filters",
                    "done",
                    "medium",
                    "sprint-1",
                    "epic-1",
                    "mock-user-4",
                    14,
                ),
                make_task(
                    "task-5",
                    "Create project CRUD operations",
                    "Implement create/read/update/delete for projects",
                    "done",
                    "high",
                    "sprint-2",
                    "epic-2",
                    "mock-user-1",
                    20,
                ),
                make_task(
                    "task-6",
                    "Implement task board view",
                    "Create Kanban board with drag and drop",
                    "done",
                    "medium",
                    "sprint-2",
                    "epic-2",
                    "mock-user-2",
                    12,
                ),
                make_task(
                    "task-7",
                    "Add drag and drop functionality",
                    "Implement DnD behaviour for backlog and board",
                    "done",
                    "medium",
                    "sprint-2",
                    "epic-2",
                    "mock-user-3",
                    10,
                ),
                make_task(
                    "task-8",
                    "Setup sprint management",
                    "Allow creating, editing, and starting sprints",
                    "done",
                    "high",
                    "sprint-2",
                    "epic-2",
                    "mock-user-4",
                    18,
                ),
                make_task(
                    "task-9",
                    "Design analytics dashboard",
                    "Create initial layout for analytics dashboard",
                    "done",
                    "medium",
                    "sprint-3",
                    "epic-3",
                    "mock-user-1",
                    10,
                ),
                make_task(
                    "task-10",
                    "Implement burndown chart",
                    "Implement burndown chart using real data",
                    "done",
                    "medium",
                    "sprint-3",
                    "epic-3",
                    "mock-user-2",
                    12,
                ),
                make_task(
                    "task-11",
                    "Create velocity chart",
                    "Implement velocity chart with historical sprints",
                    "in_review",
                    "medium",
                    "sprint-3",
                    "epic-3",
                    "mock-user-3",
                    12,
                ),
                make_task(
                    "task-12",
                    "Add CFD visualization",
                    "Implement CFD chart and data aggregation",
                    "in_progress",
                    "high",
                    "sprint-3",
                    "epic-3",
                    "mock-user-4",
                    8,
                ),
                make_task(
                    "task-13",
                    "Implement cycle time chart",
                    "Add cycle time calculation and visualization",
                    "todo",
                    "medium",
                    "sprint-3",
                    "epic-3",
                    "mock-user-1",
                    8,
                ),
                make_task(
                    "task-14",
                    "Create sprint report view",
                    "Implement sprint report view with key metrics",
                    "todo",
                    "medium",
                    "sprint-3",
                    "epic-3",
                    "mock-user-2",
                    12,
                ),
                make_task(
                    "task-15",
                    "Add export to PDF feature",
                    "Allow exporting dashboards and reports to PDF",
                    "todo",
                    "low",
                    None,
                    "epic-3",
                    None,
                    20,
                ),
                make_task(
                    "task-16",
                    "Implement email notifications",
                    "Send email updates for sprint changes and assignments",
                    "todo",
                    "medium",
                    None,
                    "epic-2",
                    None,
                    16,
                ),
                make_task(
                    "task-17",
                    "Create mobile responsive views",
                    "Ensure key pages are responsive on mobile",
                    "todo",
                    "medium",
                    None,
                    "epic-2",
                    None,
                    18,
                ),
                make_task(
                    "task-18",
                    "Add dark mode support",
                    "Implement dark mode toggle and theme",
                    "todo",
                    "low",
                    None,
                    None,
                    None,
                    10,
                ),
            ]
        )
        session.commit()

    def _to_pm_project(self, project: MockProject) -> PMProject:
        return PMProject(
            id=project.id,
            name=project.name,
            description=project.description,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    def _to_pm_user(self, user: MockUser) -> PMUser:
        return PMUser(
            id=user.id,
            name=user.name,
            email=user.email,
            raw_data={"role": user.role},
            avatar_url=user.avatar_url,
        )

    def _to_pm_sprint(self, sprint: MockSprint) -> PMSprint:
        return PMSprint(
            id=sprint.id,
            name=sprint.name,
            project_id=self.PROJECT_ID,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            status=sprint.status,
            goal=sprint.goal,
            created_at=sprint.created_at,
        )

    def _to_pm_epic(self, epic: MockEpic) -> PMEpic:
        return PMEpic(
            id=epic.id,
            name=epic.name,
            description=epic.description,
            project_id=self.PROJECT_ID,
            status=epic.status,
            created_at=epic.created_at,
        )

    def _to_pm_task(self, task: MockTask) -> PMTask:
        return PMTask(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            project_id=self.PROJECT_ID,
            epic_id=task.epic_id,
            assignee_id=task.assignee_id,
            sprint_id=task.sprint_id,
            estimated_hours=float(task.estimated_hours) if task.estimated_hours is not None else None,
            actual_hours=None,
            start_date=task.start_date,
            due_date=task.due_date,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
            raw_data={"source": "mock"},
        )

    def _random_assignee(self, session: Session) -> Optional[str]:
        user_ids = [row[0] for row in session.query(MockUser.id).all()]
        return random.choice(user_ids) if user_ids else None

    # ------------------------------------------------------------------
    # BasePMProvider implementation
    # ------------------------------------------------------------------

    async def list_projects(self) -> List[PMProject]:
        with self._session() as session:
            project = session.get(MockProject, self.PROJECT_ID)
            return [self._to_pm_project(project)] if project else []

    async def get_project(self, project_id: str) -> Optional[PMProject]:
        if project_id != self.PROJECT_ID:
            return None
        with self._session() as session:
            project = session.get(MockProject, self.PROJECT_ID)
            return self._to_pm_project(project) if project else None

    async def create_project(self, project: PMProject) -> PMProject:
        raise NotImplementedError("Mock project is predefined and cannot be created.")

    async def update_project(self, project_id: str, updates: Dict[str, Any]) -> PMProject:
        if project_id != self.PROJECT_ID:
            raise ValueError("Unknown project")
        with self._session() as session:
            record = session.get(MockProject, self.PROJECT_ID)
            if not record:
                raise ValueError("Mock project not found")
            for key, value in updates.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.commit()
            session.refresh(record)
            return self._to_pm_project(record)

    async def delete_project(self, project_id: str) -> bool:
        raise NotImplementedError("Mock project cannot be deleted.")

    async def list_tasks(
        self, project_id: Optional[str] = None, assignee_id: Optional[str] = None
    ) -> List[PMTask]:
        actual_project = self._normalize_project_id(project_id)
        with self._session() as session:
            query = session.query(MockTask).filter(MockTask.project_id == actual_project)
            if assignee_id:
                query = query.filter(MockTask.assignee_id == assignee_id)
            tasks = query.order_by(MockTask.due_date, MockTask.title).all()
            return [self._to_pm_task(t) for t in tasks]

    async def get_task(self, task_id: str) -> Optional[PMTask]:
        with self._session() as session:
            record = session.get(MockTask, task_id)
            return self._to_pm_task(record) if record else None

    async def create_task(self, task: PMTask) -> PMTask:
        actual_project = self._normalize_project_id(task.project_id)
        with self._session() as session:
            record = MockTask(
                id=f"task-{uuid4().hex[:8]}",
                project_id=actual_project,
                sprint_id=task.sprint_id,
                epic_id=task.epic_id,
                assignee_id=task.assignee_id,
                title=task.title,
                description=task.description,
                status=task.status or "todo",
                priority=task.priority or "medium",
                estimated_hours=task.estimated_hours,
                start_date=task.start_date,
                due_date=task.due_date,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return self._to_pm_task(record)

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> PMTask:
        with self._session() as session:
            record = session.get(MockTask, task_id)
            if not record:
                raise ValueError(f"Task not found: {task_id}")
            for key, value in updates.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            record.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(record)
            return self._to_pm_task(record)

    async def delete_task(self, task_id: str) -> bool:
        with self._session() as session:
            deleted = session.query(MockTask).filter_by(id=task_id).delete()
            session.commit()
            return deleted > 0

    async def list_sprints(
        self, project_id: Optional[str] = None, state: Optional[str] = None
    ) -> List[PMSprint]:
        actual_project = self._normalize_project_id(project_id)
        with self._session() as session:
            query = session.query(MockSprint).filter(MockSprint.project_id == actual_project)
            if state:
                query = query.filter(MockSprint.status == state)
            sprints = query.order_by(MockSprint.start_date).all()
            return [self._to_pm_sprint(s) for s in sprints]

    async def get_sprint(self, sprint_id: str) -> Optional[PMSprint]:
        with self._session() as session:
            sprint = session.get(MockSprint, sprint_id)
            return self._to_pm_sprint(sprint) if sprint else None

    async def create_sprint(self, sprint: PMSprint) -> PMSprint:
        actual_project = self._normalize_project_id(sprint.project_id)
        with self._session() as session:
            record = MockSprint(
                id=f"sprint-{uuid4().hex[:8]}",
                project_id=actual_project,
                name=sprint.name,
                status=sprint.status or "future",
                start_date=sprint.start_date,
                end_date=sprint.end_date,
                goal=sprint.goal,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return self._to_pm_sprint(record)

    async def update_sprint(self, sprint_id: str, updates: Dict[str, Any]) -> PMSprint:
        with self._session() as session:
            record = session.get(MockSprint, sprint_id)
            if not record:
                raise ValueError(f"Sprint not found: {sprint_id}")
            for key, value in updates.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.commit()
            session.refresh(record)
            return self._to_pm_sprint(record)

    async def delete_sprint(self, sprint_id: str) -> bool:
        with self._session() as session:
            deleted = session.query(MockSprint).filter_by(id=sprint_id).delete()
            session.commit()
            return deleted > 0

    async def list_epics(self, project_id: Optional[str] = None) -> List[PMEpic]:
        actual_project = self._normalize_project_id(project_id)
        with self._session() as session:
            epics = (
                session.query(MockEpic)
                .filter(MockEpic.project_id == actual_project)
                .order_by(MockEpic.created_at)
                .all()
            )
            return [self._to_pm_epic(e) for e in epics]

    async def get_epic(self, epic_id: str) -> Optional[PMEpic]:
        with self._session() as session:
            epic = session.get(MockEpic, epic_id)
            return self._to_pm_epic(epic) if epic else None

    async def create_epic(self, epic: PMEpic) -> PMEpic:
        actual_project = self._normalize_project_id(epic.project_id)
        with self._session() as session:
            record = MockEpic(
                id=f"epic-{uuid4().hex[:8]}",
                project_id=actual_project,
                name=epic.name,
                description=epic.description,
                status=epic.status or "todo",
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return self._to_pm_epic(record)

    async def update_epic(self, epic_id: str, updates: Dict[str, Any]) -> PMEpic:
        with self._session() as session:
            record = session.get(MockEpic, epic_id)
            if not record:
                raise ValueError(f"Epic not found: {epic_id}")
            for key, value in updates.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.commit()
            session.refresh(record)
            return self._to_pm_epic(record)

    async def delete_epic(self, epic_id: str) -> bool:
        with self._session() as session:
            deleted = session.query(MockEpic).filter_by(id=epic_id).delete()
            session.commit()
            return deleted > 0

    async def list_users(self, project_id: Optional[str] = None) -> List[PMUser]:
        with self._session() as session:
            users = session.query(MockUser).order_by(MockUser.name).all()
            return [self._to_pm_user(u) for u in users]

    async def get_user(self, user_id: str) -> Optional[PMUser]:
        with self._session() as session:
            user = session.get(MockUser, user_id)
            return self._to_pm_user(user) if user else None

    async def get_current_user(self) -> PMUser:
        users = await self.list_users()
        return users[0] if users else PMUser(id="mock-system", name="Mock User")

    async def list_statuses(
        self, entity_type: str, project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return [
            {"id": "todo", "name": "To Do", "category": "todo"},
            {"id": "in_progress", "name": "In Progress", "category": "in_progress"},
            {"id": "in_review", "name": "In Review", "category": "in_progress"},
            {"id": "done", "name": "Done", "category": "done"},
        ]

    async def get_status_transitions(self, task_id: str) -> List[PMStatusTransition]:
        statuses = await self.list_statuses("task")
        transitions: List[PMStatusTransition] = []
        for source in statuses:
            for target in statuses:
                if source["id"] != target["id"]:
                    transitions.append(
                        PMStatusTransition(
                            from_status=source["id"],
                            to_status=target["id"],
                            name=f"Move to {target['name']}",
                        )
                    )
        return transitions

    async def list_priorities(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return [
            {"id": "low", "name": "Low", "color": "#3b82f6"},
            {"id": "medium", "name": "Medium", "color": "#f59e0b"},
            {"id": "high", "name": "High", "color": "#ef4444"},
            {"id": "critical", "name": "Critical", "color": "#7c3aed"},
        ]

    async def list_components(self, project_id: str) -> List[PMComponent]:
        return []

    async def list_labels(self, project_id: Optional[str] = None) -> List[PMLabel]:
        return []

    async def get_label(self, label_id: str) -> Optional[PMLabel]:
        return None

    async def create_label(self, label: PMLabel) -> PMLabel:
        label.id = label.id or str(uuid4())
        return label

    async def update_label(self, label_id: str, updates: Dict[str, Any]) -> PMLabel:
        raise NotImplementedError("Labels are not supported in mock dataset.")

    async def delete_label(self, label_id: str) -> bool:
        return True

    async def list_comments(self, task_id: str) -> List[Dict[str, Any]]:
        return []

    async def add_comment(self, task_id: str, body: str) -> Dict[str, Any]:
        return {
            "id": str(uuid4()),
            "body": body,
            "author": {"id": "mock-user-1", "name": "Alice Johnson"},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

    # ------------------------------------------------------------------
    # Dataset regeneration via WBS LLM
    # ------------------------------------------------------------------

    async def regenerate_mock_data(self) -> Dict[str, Any]:
        llm = get_llm_by_type("basic")
        generator = WBSGenerator(llm=llm)

        wbs_result = await generator.generate_wbs(
            project_name=self.PROJECT_NAME,
            project_description=self.PROJECT_DESCRIPTION,
            project_domain="software",
            breakdown_levels=3,
            use_research=False,
        )
        wbs_structure = wbs_result.get("wbs_structure", {})
        phases = wbs_structure.get("phases", [])
        if not phases:
            raise RuntimeError("LLM did not produce any phases for the WBS.")

        with self._session() as session:
            session.query(MockTask).filter_by(project_id=self.PROJECT_ID).delete()
            session.query(MockEpic).filter_by(project_id=self.PROJECT_ID).delete()
            session.query(MockSprint).filter_by(project_id=self.PROJECT_ID).delete()
            session.commit()

            for user in self.DEFAULT_USERS:
                if not session.get(MockUser, user["id"]):
                    session.add(MockUser(**user))
            session.commit()

            today = date.today()
            phase_count = len(phases)
            closed_count = max(phase_count - 2, 0)
            active_index = closed_count if phase_count - closed_count > 0 else None

            sprint_records: Dict[str, MockSprint] = {}
            epic_records: Dict[tuple[str, str], MockEpic] = {}

            for index, phase in enumerate(phases):
                sprint_id = f"sprint-{uuid4().hex[:8]}"
                if index < closed_count:
                    status = "closed"
                    end_date = today - timedelta(days=(closed_count - index) * 7)
                    start_date = end_date - timedelta(days=13)
                elif active_index is not None and index == active_index:
                    status = "active"
                    start_date = today - timedelta(days=7)
                    end_date = today + timedelta(days=7)
                else:
                    status = "future"
                    offset = index - (active_index + 1 if active_index is not None else closed_count)
                    start_date = today + timedelta(days=14 * (offset + 1))
                    end_date = start_date + timedelta(days=13)

                sprint = MockSprint(
                    id=sprint_id,
                    project_id=self.PROJECT_ID,
                    name=phase["title"],
                    status=status,
                    start_date=start_date,
                    end_date=end_date,
                    goal=phase.get("description", ""),
                )
                session.add(sprint)
                sprint_records[phase["title"]] = sprint

                for deliverable in phase.get("deliverables", []):
                    epic_id = f"epic-{uuid4().hex[:8]}"
                    epic_status = (
                        "done" if status == "closed" else "in_progress" if status == "active" else "todo"
                    )
                    epic = MockEpic(
                        id=epic_id,
                        project_id=self.PROJECT_ID,
                        name=deliverable["title"],
                        description=deliverable.get("description", ""),
                        status=epic_status,
                    )
                    session.add(epic)
                    epic_records[(phase["title"], deliverable["title"])] = epic

            session.commit()

            user_ids = [row[0] for row in session.query(MockUser.id).all()]
            if not user_ids:
                raise RuntimeError("No mock users available to assign tasks.")

            tasks_created = 0
            for phase in phases:
                sprint = sprint_records.get(phase["title"])
                deliverables = phase.get("deliverables", [])
                if not deliverables:
                    deliverables = [{"title": f"{phase['title']} Deliverables", "tasks": []}]
                    synthetic_epic = MockEpic(
                        id=f"epic-{uuid4().hex[:8]}",
                        project_id=self.PROJECT_ID,
                        name=deliverables[0]["title"],
                        description="Auto-generated epic from WBS phase",
                        status=sprint.status if sprint else "todo",
                    )
                    session.add(synthetic_epic)
                    session.commit()
                    epic_records[(phase["title"], deliverables[0]["title"])] = synthetic_epic

                for deliverable in deliverables:
                    epic = epic_records.get((phase["title"], deliverable["title"]))
                    for task in deliverable.get("tasks", []):
                        tasks_created += 1
                        sprint_status = sprint.status if sprint else "todo"
                        task_status = (
                            "done"
                            if sprint_status == "closed"
                            else "in_progress"
                            if sprint_status == "active"
                            else "todo"
                        )

                        estimated_hours = task.get("estimated_hours") or 8.0
                        assignee_id = random.choice(user_ids)
                        start_date = sprint.start_date if sprint else today
                        due_date = sprint.end_date if sprint else start_date + timedelta(days=5)

                        session.add(
                            MockTask(
                                id=f"task-{uuid4().hex[:8]}",
                                project_id=self.PROJECT_ID,
                                sprint_id=sprint.id if sprint else None,
                                epic_id=epic.id if epic else None,
                                assignee_id=assignee_id,
                                title=task["title"],
                                description=task.get("description", ""),
                                status=task_status,
                                priority=task.get("priority", "medium"),
                                estimated_hours=estimated_hours,
                                start_date=start_date,
                                due_date=due_date,
                            )
                        )

            session.commit()

            return {
                "project_id": self.PROJECT_ID,
                "tasks": tasks_created,
                "sprints": session.query(MockSprint)
                .filter_by(project_id=self.PROJECT_ID)
                .count(),
                "epics": session.query(MockEpic)
                .filter_by(project_id=self.PROJECT_ID)
                .count(),
                "users": session.query(MockUser).count(),
                "generated_at": datetime.utcnow().isoformat(),
            }

    async def health_check(self) -> bool:
        return True

