"""
Database models for Meeting Agent.

SQLAlchemy ORM models for persisting meetings and related data.
"""

from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean,
    DateTime, Date, ForeignKey, Enum, JSON,
    create_engine,
)
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
import enum

Base = declarative_base()


class MeetingStatusDB(str, enum.Enum):
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class ActionItemStatusDB(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ActionItemPriorityDB(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MeetingDB(Base):
    """SQLAlchemy model for meetings"""
    __tablename__ = "meetings"

    id = Column(String(50), primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status
    status = Column(String(20), default=MeetingStatusDB.PENDING.value)
    error_message = Column(Text, nullable=True)
    
    # Timing
    scheduled_start = Column(DateTime, nullable=True)
    scheduled_end = Column(DateTime, nullable=True)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # File info
    file_path = Column(String(1000), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    audio_format = Column(String(20), nullable=True)
    
    # PM Integration
    project_id = Column(String(200), nullable=True)
    user_id = Column(String(100), nullable=True)
    
    # Metadata
    platform = Column(String(50), nullable=True)
    extra_metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    participants = relationship("ParticipantDB", back_populates="meeting", cascade="all, delete-orphan")
    transcript_segments = relationship("TranscriptSegmentDB", back_populates="meeting", cascade="all, delete-orphan")
    action_items = relationship("ActionItemDB", back_populates="meeting", cascade="all, delete-orphan")
    decisions = relationship("DecisionDB", back_populates="meeting", cascade="all, delete-orphan")
    summary = relationship("MeetingSummaryDB", back_populates="meeting", uselist=False, cascade="all, delete-orphan")


class ParticipantDB(Base):
    """SQLAlchemy model for meeting participants"""
    __tablename__ = "meeting_participants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(String(50), ForeignKey("meetings.id"), nullable=False)
    
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=True)
    role = Column(String(50), default="participant")
    pm_user_id = Column(String(100), nullable=True)
    speaking_time_seconds = Column(Float, nullable=True)
    
    meeting = relationship("MeetingDB", back_populates="participants")


class TranscriptSegmentDB(Base):
    """SQLAlchemy model for transcript segments"""
    __tablename__ = "transcript_segments"

    id = Column(String(50), primary_key=True)
    meeting_id = Column(String(50), ForeignKey("meetings.id"), nullable=False)
    
    speaker = Column(String(200), nullable=True)
    speaker_id = Column(String(100), nullable=True)
    text = Column(Text, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    
    meeting = relationship("MeetingDB", back_populates="transcript_segments")


class ActionItemDB(Base):
    """SQLAlchemy model for action items"""
    __tablename__ = "action_items"

    id = Column(String(50), primary_key=True)
    meeting_id = Column(String(50), ForeignKey("meetings.id"), nullable=False)
    
    description = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    
    assignee_name = Column(String(200), nullable=True)
    assignee_id = Column(String(100), nullable=True)
    
    due_date = Column(Date, nullable=True)
    due_date_text = Column(String(200), nullable=True)
    
    priority = Column(String(20), default=ActionItemPriorityDB.MEDIUM.value)
    status = Column(String(20), default=ActionItemStatusDB.PENDING.value)
    
    source_quote = Column(Text, nullable=True)
    source_timestamp = Column(Float, nullable=True)
    
    pm_task_id = Column(String(100), nullable=True)
    pm_task_url = Column(String(500), nullable=True)
    
    confidence = Column(Float, default=0.8)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    meeting = relationship("MeetingDB", back_populates="action_items")


class DecisionDB(Base):
    """SQLAlchemy model for decisions"""
    __tablename__ = "decisions"

    id = Column(String(50), primary_key=True)
    meeting_id = Column(String(50), ForeignKey("meetings.id"), nullable=False)
    
    summary = Column(Text, nullable=False)
    details = Column(Text, nullable=True)
    decision_type = Column(String(50), default="agreement")
    
    decision_makers = Column(JSON, default=list)
    stakeholders = Column(JSON, default=list)
    impact_areas = Column(JSON, default=list)
    
    source_quote = Column(Text, nullable=True)
    source_timestamp = Column(Float, nullable=True)
    
    confidence = Column(Float, default=0.8)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    meeting = relationship("MeetingDB", back_populates="decisions")


class MeetingSummaryDB(Base):
    """SQLAlchemy model for meeting summaries"""
    __tablename__ = "meeting_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(String(50), ForeignKey("meetings.id"), unique=True, nullable=False)
    
    executive_summary = Column(Text, nullable=False)
    key_points = Column(JSON, default=list)
    topics = Column(JSON, default=list)
    participant_contributions = Column(JSON, default=dict)
    
    overall_sentiment = Column(String(20), nullable=True)
    model_used = Column(String(50), nullable=True)
    
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    meeting = relationship("MeetingDB", back_populates="summary")


def create_database(database_url: str = "sqlite:///./data/meetings.db"):
    """Create database and tables"""
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Get a database session"""
    Session = sessionmaker(bind=engine)
    return Session()
