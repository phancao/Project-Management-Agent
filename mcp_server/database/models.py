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









