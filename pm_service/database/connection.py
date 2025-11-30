# PM Service Database Connection
"""
Database connection management for PM Service.
Uses the same database as MCP Server for provider configurations.
"""

import logging
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from pm_service.config import settings

logger = logging.getLogger(__name__)

# Create engine
engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.debug,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db_session() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    from .models import Base as ModelsBase
    ModelsBase.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")


def check_db_connection() -> bool:
    """Check if database is connected."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

