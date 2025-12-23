"""
SQLAlchemy ORM models for Project Management Agent

These models match the database schema in database/schema.sql
"""

from typing import List, Optional

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    ARRAY,
    JSON,
    Date,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()  # type: ignore


class SearchProviderAPIKey(Base):  # type: ignore
    """Search Provider API Key model for storing search provider credentials"""
    __tablename__ = "search_provider_api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(String(50), nullable=False, unique=True)  # 'tavily', 'brave_search', etc.
    provider_name = Column(String(255), nullable=False)
    api_key = Column(String(1000), nullable=True)
    base_url = Column(String(500), nullable=True)  # Optional custom base URL
    additional_config = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):  # type: ignore
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


class Project(Base):  # type: ignore
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


class ProjectGoal(Base):  # type: ignore
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


class TeamMember(Base):  # type: ignore
    """Team member model"""
    __tablename__ = "team_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    role = Column(String(100))
    skills: Column[List[Optional[str]]] = Column(ARRAY(Text))  # type: ignore[assignment]
    hourly_rate = Column(Float)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="team_members")

    __table_args__ = (
        {"schema": "public"},
    )


class Task(Base):  # type: ignore
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


class TaskDependency(Base):  # type: ignore
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


class ResearchSession(Base):  # type: ignore
    """Research session model"""
    __tablename__ = "research_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    topic = Column(Text, nullable=False)
    research_type = Column(String(50), default='general')
    status = Column(String(50), default='active')
    research_data = Column(JSON)
    findings = Column(Text)
    sources: Column[List[Optional[str]]] = Column(ARRAY(Text))  # type: ignore[assignment]
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="research_sessions")


class KnowledgeBaseItem(Base):  # type: ignore
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


class ConversationSession(Base):  # type: ignore
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


class ConversationMessage(Base):  # type: ignore
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


# ==================== Mock Provider Tables ====================


class ProjectTemplate(Base):  # type: ignore
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


class ProjectMetric(Base):  # type: ignore
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


class IntentClassification(Base):  # type: ignore
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


class IntentFeedback(Base):  # type: ignore
    """User feedback on intent classification"""
    __tablename__ = "intent_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    classification_id = Column(UUID(as_uuid=True), ForeignKey("intent_classifications.id"))
    feedback_type = Column(String(20), nullable=False)
    original_message = Column(Text)
    suggested_intent = Column(String(50))
    user_comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class IntentMetric(Base):  # type: ignore
    """Intent classification success metrics"""
    __tablename__ = "intent_metrics"

    intent_type = Column(String(50), primary_key=True)
    total_classifications = Column(Integer, default=0)
    correct_classifications = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    average_confidence = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)


class LearnedIntentPattern(Base):  # type: ignore
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


class Sprint(Base):  # type: ignore
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


class SprintTask(Base):  # type: ignore
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


class PMProviderConnection(Base):  # type: ignore
    """PM provider connection model"""
    __tablename__ = "pm_provider_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    provider_type = Column(String(50), nullable=False)
    base_url = Column(String(500), nullable=False)
    api_key = Column(String(500), nullable=True)
    api_token = Column(String(500), nullable=True)
    username = Column(String(255), nullable=True)
    organization_id = Column(String(255), nullable=True)
    project_key = Column(String(255), nullable=True)
    workspace_id = Column(String(255), nullable=True)
    additional_config = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync_at = Column(DateTime, nullable=True)


class ProjectSyncMapping(Base):  # type: ignore
    """Project sync mapping model"""
    __tablename__ = "project_sync_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    internal_project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    provider_connection_id = Column(UUID(as_uuid=True), ForeignKey("pm_provider_connections.id", ondelete="CASCADE"))
    external_project_id = Column(String(255), nullable=False)
    sync_enabled = Column(Boolean, default=True)
    last_sync_at = Column(DateTime, nullable=True)
    sync_config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserMCPAPIKey(Base):  # type: ignore
    """User MCP API Key model for external client authentication"""
    __tablename__ = "user_mcp_api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    api_key = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=True)  # Optional: "Cursor", "VS Code", etc.
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIProviderAPIKey(Base):  # type: ignore
    """AI Provider API Key model for storing LLM provider credentials"""
    __tablename__ = "ai_provider_api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(String(50), nullable=False, unique=True)  # 'openai', 'anthropic', etc.
    provider_name = Column(String(255), nullable=False)
    api_key = Column(String(1000), nullable=True)
    base_url = Column(String(500), nullable=True)  # Optional custom base URL
    model_name = Column(String(255), nullable=True)  # Optional default model
    additional_config = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="mcp_api_keys")


class Meeting(Base):  # type: ignore
    """Meeting model"""
    __tablename__ = "meetings"

    id = Column(String(50), primary_key=True)  # 'mtg_' prefix
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Timing
    scheduled_start = Column(DateTime, nullable=True)
    scheduled_end = Column(DateTime, nullable=True)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    
    # Status
    status = Column(String(50), default='pending', nullable=False)
    error_message = Column(Text, nullable=True)
    
    # File info
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    audio_format = Column(String(50), nullable=True)
    
    # Integration
    project_id = Column(String(50), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    participants = relationship("MeetingParticipant", back_populates="meeting", cascade="all, delete-orphan")
    transcript = relationship("Transcript", uselist=False, back_populates="meeting", cascade="all, delete-orphan")
    action_items = relationship("MeetingActionItem", back_populates="meeting", cascade="all, delete-orphan")
    decisions = relationship("MeetingDecision", back_populates="meeting", cascade="all, delete-orphan")
    summaries = relationship("MeetingSummary", back_populates="meeting", cascade="all, delete-orphan")


class MeetingParticipant(Base):  # type: ignore
    """Meeting participant model"""
    __tablename__ = "meeting_participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(String(50), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    role = Column(String(50), default='participant')
    speaking_time_seconds = Column(Float, nullable=True)
    pm_user_id = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="participants")


class Transcript(Base):  # type: ignore
    """Meeting transcript model"""
    __tablename__ = "transcripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(String(50), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True)
    language = Column(String(10), default='en')
    full_text = Column(Text, nullable=True)
    word_count = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="transcript")
    segments = relationship("TranscriptSegment", back_populates="transcript", cascade="all, delete-orphan")


class TranscriptSegment(Base):  # type: ignore
    """Transcript segment model"""
    __tablename__ = "transcript_segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcript_id = Column(UUID(as_uuid=True), ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False)
    segment_index = Column(Integer, nullable=False)
    speaker = Column(String(255), nullable=True)
    speaker_id = Column(UUID(as_uuid=True), ForeignKey("meeting_participants.id", ondelete="SET NULL"), nullable=True)
    text = Column(Text, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    transcript = relationship("Transcript", back_populates="segments")


class MeetingActionItem(Base):  # type: ignore
    """Meeting action item model"""
    __tablename__ = "meeting_action_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(String(50), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), default='pending')
    
    assignee_name = Column(String(255), nullable=True)
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("meeting_participants.id", ondelete="SET NULL"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    
    pm_task_id = Column(String(255), nullable=True)
    original_text = Column(String(500), nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="action_items")


class MeetingDecision(Base):  # type: ignore
    """Meeting decision model"""
    __tablename__ = "meeting_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(String(50), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="decisions")


class MeetingSummary(Base):  # type: ignore
    """Meeting summary model"""
    __tablename__ = "meeting_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(String(50), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    summary_type = Column(String(50), default='executive')
    content = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="summaries")

