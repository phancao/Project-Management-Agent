"""
Database connection utilities
"""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Database URL from environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://pm_user:pm_password@localhost:5432/project_management"
)

# Create SQLAlchemy engine
# For PostgreSQL with psycopg, we don't need StaticPool
# StaticPool is mainly for SQLite in-memory databases
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=20,
    echo=False  # Set to True for SQL query logging
)

# Create SessionLocal class
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db_engine():
    """Get the database engine"""
    return engine


def get_db_session() -> Generator[Session, None, None]:
    """
    Dependency function that provides a database session
    
    Usage:
        from database import get_db_session
        
        def some_function():
            db = get_db_session()
            try:
                # Use db session
                projects = db.query(Project).all()
            finally:
                db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize the database by creating all tables
    Note: This should be called after all models are imported
    """
    import logging
    logger = logging.getLogger(__name__)
    # Import all models to ensure they're registered with Base
    from database.orm_models import (
        Base, User, Project, ProjectGoal, TeamMember, Task, TaskDependency,
        ResearchSession, KnowledgeBaseItem, ConversationSession, ConversationMessage,
        ProjectTemplate, ProjectMetric, IntentClassification, IntentFeedback,
        IntentMetric, LearnedIntentPattern
    )
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}")


def close_db():
    """Close database connections"""
    engine.dispose()

