"""
SQLAlchemy ORM models for Project Management Agent

These models match the database schema in database/schema.sql
"""

from sqlalchemy import Column, String, Text, Integer, Float, DateTime, Boolean, ForeignKey, ARRAY, JSON, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), default='user')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projects = relationship("Project", back_populates="creator")
    conversation_sessions = relationship("ConversationSession", back_populates="user")


class Project(Base):
    """Project model"""
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    domain = Column(String(100))
    status = Column(String(50), default='planning')
    priority = Column(String(20), default='medium')
    timeline_weeks = Column(Integer)
    budget = Column(Float)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    creator = relationship("User", back_populates="projects")
    goals = relationship("ProjectGoal", back_populates="project", cascade="all, delete-orphan")
    team_members = relationship("TeamMember", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    research_sessions = relationship("ResearchSession", back_populates="project", cascade="all, delete-orphan")
    metrics = relationship("ProjectMetric", back_populates="project", cascade="all, delete-orphan")
    sprints = relationship("Sprint", back_populates="project", cascade="all, delete-orphan")


class ProjectGoal(Base):
    """Project goal model"""
    __tablename__ = "project_goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    goal_text = Column(Text, nullable=False)
    priority = Column(Integer, default=1)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="goals")


class TeamMember(Base):
    """Team member model"""
    __tablename__ = "team_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    role = Column(String(100))
    skills = Column(ARRAY(Text))
    hourly_rate = Column(Float)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="team_members")

    __table_args__ = (
        {"schema": "public"},
    )


class Task(Base):
    """Task model"""
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default='todo')
    priority = Column(String(20), default='medium')
    estimated_hours = Column(Float)
    actual_hours = Column(Float, default=0)
    assigned_to = Column(UUID(as_uuid=True), nullable=True)
    # Note: ForeignKey to team_members.id removed to fix SQLAlchemy relationship issue
    # The FK is still in the database schema, but ORM doesn't enforce it
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="tasks")
    subtasks = relationship("Task", back_populates="parent_task", cascade="all, delete-orphan", foreign_keys=[parent_task_id])
    parent_task = relationship("Task", remote_side=[id], back_populates="subtasks")
    # dependencies = relationship("TaskDependency", back_populates="task", cascade="all, delete-orphan")  # Commented out to avoid SQLAlchemy join ambiguity


class TaskDependency(Base):
    """Task dependency model"""
    __tablename__ = "task_dependencies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"))
    depends_on_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"))
    dependency_type = Column(String(20), default='finish_to_start')
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    # task = relationship("Task", foreign_keys=[task_id], back_populates="dependencies")  # Commented out to avoid SQLAlchemy join ambiguity

    __table_args__ = (
        {"schema": "public"},
    )


class ResearchSession(Base):
    """Research session model"""
    __tablename__ = "research_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    topic = Column(Text, nullable=False)
    research_type = Column(String(50), default='general')
    status = Column(String(50), default='active')
    research_data = Column(JSON)
    findings = Column(Text)
    sources = Column(ARRAY(Text))
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="research_sessions")


class KnowledgeBaseItem(Base):
    """Knowledge base item model with vector embeddings"""
    __tablename__ = "knowledge_base"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default='text')
    # Note: Vector embedding column is created by pgvector extension
    # For now, we'll store it as JSON until we add pgvector support
    embedding = Column(JSON, nullable=True)  # Will be changed to Vector type when pgvector is added
    metadata_json = Column("metadata", JSON)  # Rename to avoid conflict with SQLAlchemy metadata
    source_type = Column(String(50))  # 'research', 'project', 'manual'
    source_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConversationSession(Base):
    """Conversation session model"""
    __tablename__ = "conversation_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    session_id = Column(String(255), unique=True, nullable=False)
    current_state = Column(String(50), default='intent_detection')
    intent = Column(String(50), nullable=True)
    context_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="conversation_sessions")
    messages = relationship("ConversationMessage", back_populates="session", cascade="all, delete-orphan")


class ConversationMessage(Base):
    """Conversation message model"""
    __tablename__ = "conversation_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("conversation_sessions.id", ondelete="CASCADE"))
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    metadata_json = Column("metadata", JSON)  # Rename to avoid conflict
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("ConversationSession", back_populates="messages")


class ProjectTemplate(Base):
    """Project template model"""
    __tablename__ = "project_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    domain = Column(String(100))
    template_data = Column(JSON, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjectMetric(Base):
    """Project metric model"""
    __tablename__ = "project_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    metric_type = Column(String(50), nullable=False)
    metric_value = Column(Float)
    metric_unit = Column(String(20))
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="metrics")


class IntentClassification(Base):
    """Intent classification history for self-learning"""
    __tablename__ = "intent_classifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Note: session_id refers to conversation_sessions(id) which is UUID, 
    # but we store it as string session_id from conversation context
    session_id = Column(UUID(as_uuid=True), nullable=True)  # Can be NULL for now
    message = Column(Text, nullable=False)
    classified_intent = Column(String(50), nullable=False)
    confidence_score = Column(Float, default=0.0)
    was_correct = Column(Boolean, nullable=True)
    user_corrected_intent = Column(String(50), nullable=True)
    conversation_history = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class IntentFeedback(Base):
    """User feedback on intent classification"""
    __tablename__ = "intent_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    classification_id = Column(UUID(as_uuid=True), ForeignKey("intent_classifications.id"))
    feedback_type = Column(String(20), nullable=False)
    original_message = Column(Text)
    suggested_intent = Column(String(50))
    user_comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class IntentMetric(Base):
    """Intent classification success metrics"""
    __tablename__ = "intent_metrics"

    intent_type = Column(String(50), primary_key=True)
    total_classifications = Column(Integer, default=0)
    correct_classifications = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    average_confidence = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)


class LearnedIntentPattern(Base):
    """Learned patterns for intent classification"""
    __tablename__ = "learned_intent_patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intent_type = Column(String(50), nullable=False)
    pattern_text = Column(Text, nullable=False)
    success_count = Column(Integer, default=1)
    failure_count = Column(Integer, default=0)
    pattern_type = Column(String(20), default="keyword")
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow)


class Sprint(Base):
    """Sprint model"""
    __tablename__ = "sprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    duration_weeks = Column(Integer)
    duration_days = Column(Integer)
    capacity_hours = Column(Float)
    planned_hours = Column(Float)
    utilization = Column(Float)  # percentage
    status = Column(String(50), default='planned')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="sprints")
    sprint_tasks = relationship("SprintTask", back_populates="sprint", cascade="all, delete-orphan")


class SprintTask(Base):
    """Sprint task junction model"""
    __tablename__ = "sprint_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sprint_id = Column(UUID(as_uuid=True), ForeignKey("sprints.id", ondelete="CASCADE"))
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"))
    assigned_to_name = Column(String(255))
    capacity_used = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sprint = relationship("Sprint", back_populates="sprint_tasks")
    task = relationship("Task", foreign_keys=[task_id])

