"""
MCP Server Database Connection

Independent database connection for MCP Server.
This is completely separate from the backend database.
"""

import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from ..config import PMServerConfig

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine = None
_session_factory = None


def init_mcp_db(config: PMServerConfig | None = None) -> None:
    """
    Initialize MCP Server database connection.
    
    Args:
        config: PMServerConfig instance. If None, creates from environment.
    """
    global _engine, _session_factory
    
    if config is None:
        from ..config import PMServerConfig
        config = PMServerConfig.from_env()
    
    database_url = config.database_url
    
    logger.info(f"Initializing MCP Server database: {database_url.split('@')[-1] if '@' in database_url else database_url}")
    
    # Create engine with connection pooling
    _engine = create_engine(
        database_url,
        poolclass=NullPool,  # Use NullPool for serverless/containerized deployments
        echo=False,
        future=True,
    )
    
    # Create session factory
    _session_factory = sessionmaker(
        bind=_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    
    logger.info("MCP Server database connection initialized")


def get_mcp_db_session() -> Generator[Session, None, None]:
    """
    Get MCP Server database session.
    
    This is independent from the backend database session.
    
    Yields:
        SQLAlchemy Session for MCP Server database
    """
    global _session_factory
    
    if _session_factory is None:
        init_mcp_db()
    
    db = _session_factory()
    try:
        yield db
    except Exception as e:
        logger.error(f"MCP Server database session error: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


def get_mcp_db_engine():
    """Get the MCP Server database engine."""
    global _engine
    
    if _engine is None:
        init_mcp_db()
    
    return _engine









