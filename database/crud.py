"""
CRUD operations for Project Management Agent
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from database.orm_models import (
    User, Project, Task, ProjectGoal, TeamMember, TaskDependency,
    ResearchSession, KnowledgeBaseItem, ConversationSession, ConversationMessage,
    ProjectTemplate, ProjectMetric
)


# ==================== USER CRUD ====================

def create_user(db: Session, email: str, name: str, role: str = "user") -> User:
    """Create a new user"""
    user = User(email=email, name=name, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user(db: Session, user_id: UUID) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Get all users with pagination"""
    return db.query(User).offset(skip).limit(limit).all()


# ==================== PROJECT CRUD ====================

def create_project(db: Session, name: str, description: str, created_by: UUID,
                   domain: Optional[str] = None, priority: str = "medium",
                   timeline_weeks: Optional[int] = None,
                   budget: Optional[float] = None) -> Project:
    """Create a new project"""
    project = Project(
        name=name,
        description=description,
        created_by=created_by,
        domain=domain,
        priority=priority,
        timeline_weeks=timeline_weeks,
        budget=budget,
        status="planning"
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_project(db: Session, project_id: UUID) -> Optional[Project]:
    """Get project by ID"""
    return db.query(Project).filter(Project.id == project_id).first()


def get_projects(db: Session, skip: int = 0, limit: int = 100,
                 user_id: Optional[UUID] = None,
                 status: Optional[str] = None) -> List[Project]:
    """Get all projects with optional filters"""
    query = db.query(Project)
    
    if user_id:
        query = query.filter(Project.created_by == user_id)
    if status:
        query = query.filter(Project.status == status)
    
    return query.offset(skip).limit(limit).all()


def update_project(db: Session, project_id: UUID, **kwargs) -> Optional[Project]:
    """Update project by ID"""
    project = get_project(db, project_id)
    if not project:
        return None
    
    for key, value in kwargs.items():
        if hasattr(project, key) and value is not None:
            setattr(project, key, value)
    
    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: UUID) -> bool:
    """Delete project by ID"""
    project = get_project(db, project_id)
    if not project:
        return False
    
    db.delete(project)
    db.commit()
    return True


# ==================== TASK CRUD ====================

def create_task(db: Session, project_id: UUID, title: str,
                description: Optional[str] = None,
                priority: str = "medium",
                estimated_hours: Optional[float] = None,
                due_date: Optional[datetime] = None,
                assigned_to: Optional[UUID] = None,
                parent_task_id: Optional[UUID] = None) -> Task:
    """Create a new task"""
    task = Task(
        project_id=project_id,
        title=title,
        description=description,
        priority=priority,
        estimated_hours=estimated_hours,
        due_date=due_date,
        assigned_to=assigned_to,
        parent_task_id=parent_task_id,
        status="todo"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: UUID) -> Optional[Task]:
    """Get task by ID"""
    return db.query(Task).filter(Task.id == task_id).first()


def get_tasks_by_project(db: Session, project_id: UUID,
                         status: Optional[str] = None) -> List[Task]:
    """Get all tasks for a project"""
    query = db.query(Task).filter(Task.project_id == project_id)
    
    if status:
        query = query.filter(Task.status == status)
    
    return query.all()


def update_task(db: Session, task_id: UUID, **kwargs) -> Optional[Task]:
    """Update task by ID"""
    task = get_task(db, task_id)
    if not task:
        return None
    
    for key, value in kwargs.items():
        if hasattr(task, key) and value is not None:
            setattr(task, key, value)
    
    if 'status' in kwargs and kwargs['status'] == 'completed':
        task.completed_at = datetime.utcnow()
    
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: UUID) -> bool:
    """Delete task by ID"""
    task = get_task(db, task_id)
    if not task:
        return False
    
    db.delete(task)
    db.commit()
    return True


# ==================== TEAM MEMBER CRUD ====================

def create_team_member(db: Session, project_id: UUID, user_id: UUID,
                       role: Optional[str] = None,
                       skills: Optional[List[str]] = None,
                       hourly_rate: Optional[float] = None) -> TeamMember:
    """Add a team member to a project
    
    Args:
        project_id: Project to add member to
        user_id: User to add as team member
        role: Role in the project
        skills: List of skills
        hourly_rate: Hourly rate for the member
    """
    member = TeamMember(
        project_id=project_id,
        user_id=user_id,
        role=role,
        skills=skills,
        hourly_rate=hourly_rate
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def get_team_members_by_project(db: Session, project_id: UUID) -> List[TeamMember]:
    """Get all team members for a project"""
    return db.query(TeamMember).filter(TeamMember.project_id == project_id).all()


def delete_team_member(db: Session, member_id: UUID) -> bool:
    """Remove a team member from a project"""
    member = db.query(TeamMember).filter(TeamMember.id == member_id).first()
    if not member:
        return False
    
    db.delete(member)
    db.commit()
    return True


# ==================== RESEARCH SESSION CRUD ====================

def create_research_session(db: Session, topic: str,
                            project_id: Optional[UUID] = None,
                            research_type: str = "general") -> ResearchSession:
    """Create a new research session"""
    session = ResearchSession(
        topic=topic,
        project_id=project_id,
        research_type=research_type,
        status="active"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_research_session(db: Session, session_id: UUID) -> Optional[ResearchSession]:
    """Get research session by ID"""
    return db.query(ResearchSession).filter(ResearchSession.id == session_id).first()


def get_research_sessions_by_project(db: Session, project_id: UUID) -> List[ResearchSession]:
    """Get all research sessions for a project"""
    return db.query(ResearchSession).filter(ResearchSession.project_id == project_id).all()


def update_research_session(db: Session, session_id: UUID,
                           research_data: Optional[Dict[str, Any]] = None,
                           findings: Optional[str] = None,
                           sources: Optional[List[str]] = None,
                           status: Optional[str] = None) -> Optional[ResearchSession]:
    """Update research session"""
    session = get_research_session(db, session_id)
    if not session:
        return None
    
    if research_data is not None:
        session.research_data = research_data
    if findings is not None:
        session.findings = findings
    if sources is not None:
        session.sources = sources
    if status is not None:
        session.status = status
        if status == "completed":
            session.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(session)
    return session


# ==================== CONVERSATION SESSION CRUD ====================

def create_conversation_session(db: Session, user_id: UUID, session_id: str) -> ConversationSession:
    """Create a new conversation session"""
    session = ConversationSession(
        user_id=user_id,
        session_id=session_id,
        current_state="intent_detection"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_conversation_session(db: Session, session_id: str) -> Optional[ConversationSession]:
    """Get conversation session by session_id"""
    return db.query(ConversationSession).filter(
        ConversationSession.session_id == session_id
    ).first()


def update_conversation_session(db: Session, session_id: str, **kwargs) -> Optional[ConversationSession]:
    """Update conversation session"""
    session = get_conversation_session(db, session_id)
    if not session:
        return None
    
    for key, value in kwargs.items():
        if hasattr(session, key) and value is not None:
            setattr(session, key, value)
    
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session


def create_conversation_message(db: Session, session_id: UUID, role: str, content: str,
                                metadata: Optional[Dict[str, Any]] = None) -> ConversationMessage:
    """Create a new conversation message"""
    message = ConversationMessage(
        session_id=session_id,
        role=role,
        content=content,
        metadata=metadata or {}
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_conversation_messages(db: Session, session_id: UUID, limit: int = 100) -> List[ConversationMessage]:
    """Get conversation messages for a session"""
    return db.query(ConversationMessage).filter(
        ConversationMessage.session_id == session_id
    ).order_by(ConversationMessage.created_at.desc()).limit(limit).all()


# ==================== KNOWLEDGE BASE CRUD ====================

def create_knowledge_item(db: Session, content: str,
                          content_type: str = "text",
                          embedding: Optional[List[float]] = None,
                          metadata: Optional[Dict[str, Any]] = None,
                          source_type: Optional[str] = None,
                          source_id: Optional[UUID] = None) -> KnowledgeBaseItem:
    """Create a new knowledge base item"""
    item = KnowledgeBaseItem(
        content=content,
        content_type=content_type,
        embedding=embedding,
        metadata=metadata or {},
        source_type=source_type,
        source_id=source_id
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_knowledge_items(db: Session, source_type: Optional[str] = None,
                       limit: int = 100) -> List[KnowledgeBaseItem]:
    """Get knowledge base items with optional filters"""
    query = db.query(KnowledgeBaseItem)
    
    if source_type:
        query = query.filter(KnowledgeBaseItem.source_type == source_type)
    
    return query.order_by(KnowledgeBaseItem.created_at.desc()).limit(limit).all()


def search_knowledge(db: Session, query_text: str, limit: int = 10) -> List[KnowledgeBaseItem]:
    """Search knowledge base by content (basic text search)"""
    # TODO: Implement semantic search using vector embeddings
    return db.query(KnowledgeBaseItem).filter(
        KnowledgeBaseItem.content.ilike(f"%{query_text}%")
    ).limit(limit).all()

