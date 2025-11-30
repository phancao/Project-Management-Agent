# PM Service Database Models
"""
SQLAlchemy models for PM Service.
Uses the same schema as MCP Server for provider configurations.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class PMProviderConnection(Base):
    """PM Provider connection configuration."""
    
    __tablename__ = "pm_provider_connections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    provider_type = Column(String(50), nullable=False)  # openproject, jira, clickup
    base_url = Column(String(500), nullable=False)
    api_key = Column(Text, nullable=True)  # Encrypted in production
    api_token = Column(Text, nullable=True)
    username = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync_at = Column(DateTime, nullable=True)
    backend_provider_id = Column(UUID(as_uuid=True), nullable=True, unique=True)
    additional_config = Column(JSON, nullable=True)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "provider_type": self.provider_type,
            "base_url": self.base_url,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
        }
    
    def get_provider_config(self) -> dict[str, Any]:
        """Get configuration for creating provider instance."""
        config = {
            "provider_type": self.provider_type,
            "base_url": self.base_url,
        }
        
        if self.api_key:
            config["api_key"] = self.api_key
        if self.api_token:
            config["api_token"] = self.api_token
        if self.username:
            config["username"] = self.username
        if self.additional_config:
            # Filter out non-provider config keys
            allowed_keys = {"organization_id", "workspace_id", "project_key"}
            filtered_config = {k: v for k, v in self.additional_config.items() if k in allowed_keys}
            config.update(filtered_config)
        
        return config

