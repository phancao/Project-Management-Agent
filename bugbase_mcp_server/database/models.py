# Copyright (c) 2025 Galaxy Technology Service
# BugBase MCP Server - SQLAlchemy Models

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class Bug(Base):
    """Bug report model."""
    __tablename__ = "bugs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    status = Column(String(20), default="open")  # open, in_progress, fixed, closed
    screenshot_path = Column(String(500), nullable=True)
    navigation_history = Column(JSONB, nullable=True)
    page_url = Column(String(500), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    comments = relationship("BugComment", back_populates="bug", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_bugs_status", "status"),
        Index("idx_bugs_severity", "severity"),
        Index("idx_bugs_created_at", "created_at"),
    )

    def to_dict(self, include_comments: bool = False) -> dict:
        """Convert to dictionary."""
        result = {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "status": self.status,
            "screenshot_path": self.screenshot_path,
            "navigation_history": self.navigation_history,
            "page_url": self.page_url,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_comments:
            result["comments"] = [c.to_dict() for c in self.comments]
        return result


class BugComment(Base):
    """Comment on a bug report."""
    __tablename__ = "bug_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bug_id = Column(UUID(as_uuid=True), ForeignKey("bugs.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(50), default="user")  # user, ai
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    bug = relationship("Bug", back_populates="comments")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "bug_id": str(self.bug_id),
            "content": self.content,
            "author": self.author,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
