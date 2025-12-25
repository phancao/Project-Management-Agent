"""
MCP Server Database Models

Independent ORM models for MCP Server database.
This is completely separate from the backend database models.
"""

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Integer,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    """User model for MCP Server"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    mcp_api_keys = relationship("UserMCPAPIKey", back_populates="user", cascade="all, delete-orphan")
    provider_connections = relationship("PMProviderConnection", back_populates="user", cascade="all, delete-orphan")


class UserMCPAPIKey(Base):
    """User API Keys for MCP Server access"""
    __tablename__ = "user_mcp_api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    api_key = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="mcp_api_keys")


class PMProviderConnection(Base):
    """PM Provider Connection model for MCP Server"""
    __tablename__ = "pm_provider_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    provider_type = Column(String(50), nullable=False)  # 'openproject', 'jira', 'clickup', etc.
    base_url = Column(String(500), nullable=False)
    api_key = Column(String(500), nullable=True)
    api_token = Column(String(500), nullable=True)
    username = Column(String(255), nullable=True)
    organization_id = Column(String(255), nullable=True)
    project_key = Column(String(255), nullable=True)
    workspace_id = Column(String(255), nullable=True)
    additional_config = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync_at = Column(DateTime, nullable=True)
    # Backend provider ID - used to map backend provider IDs to MCP provider IDs
    backend_provider_id = Column(UUID(as_uuid=True), nullable=True, unique=True)

    # Relationships
    user = relationship("User", back_populates="provider_connections")










class Meeting(Base):
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


class MeetingParticipant(Base):
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


class Transcript(Base):
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


class TranscriptSegment(Base):
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


class MeetingActionItem(Base):
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


class MeetingDecision(Base):
    """Meeting decision model"""
    __tablename__ = "meeting_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(String(50), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="decisions")


class MeetingSummary(Base):
    """Meeting summary model"""
    __tablename__ = "meeting_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(String(50), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    summary_type = Column(String(50), default='executive')
    content = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="summaries")
