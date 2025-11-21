"""
Database connection utilities
"""

import os
import logging
from typing import Generator
from urllib.parse import urlparse, urlunparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)


def _is_running_in_docker() -> bool:
    """
    Detect if code is running inside a Docker container.
    
    Returns:
        True if running in Docker, False otherwise
    """
    # Check for Docker-specific files
    if os.path.exists("/.dockerenv"):
        return True
    
    # Check cgroup (more reliable)
    try:
        with open("/proc/self/cgroup", "r", encoding="utf-8") as f:
            content = f.read()
            if "docker" in content or "containerd" in content:
                return True
    except (FileNotFoundError, IOError):
        pass
    
    return False


def _convert_localhost_to_docker_service(database_url: str) -> str:
    """
    Convert localhost URLs to Docker service names when running in containers.
    
    This fixes connection issues where containers try to connect to localhost
    but need to use Docker service names instead.
    
    Args:
        database_url: Original database URL (may contain localhost)
        
    Returns:
        Converted URL with Docker service name if applicable
    """
    if not _is_running_in_docker():
        return database_url
    
    try:
        parsed = urlparse(database_url)
        hostname = parsed.hostname
        port = parsed.port or 5432
        
        # Map localhost:port to Docker service names
        # Based on docker-compose.yml service definitions
        # NOTE: OpenProject databases (5433, 5434) are NOT included here because
        # OpenProject is a separate system that should only be accessed via API.
        # Direct database access to OpenProject is not allowed.
        docker_service_map = {
            5432: "postgres",           # Main PostgreSQL database
            5435: "mcp_postgres",       # MCP Server database
        }
        
        if hostname in ("localhost", "127.0.0.1") and port in docker_service_map:
            service_name = docker_service_map[port]
            # Reconstruct netloc preserving username, password, and port
            # Format: username:password@hostname:port
            if parsed.username and parsed.password:
                new_netloc = f"{parsed.username}:{parsed.password}@{service_name}:{port}"
            elif parsed.username:
                new_netloc = f"{parsed.username}@{service_name}:{port}"
            else:
                new_netloc = f"{service_name}:{port}"
            
            new_parsed = parsed._replace(netloc=new_netloc)
            new_url = urlunparse(new_parsed)
            logger.info(
                "Converting localhost database URL to Docker service: %s -> %s",
                database_url,
                new_url
            )
            return new_url
    except (ValueError, AttributeError) as e:
        logger.warning(
            "Failed to convert localhost database URL %s: %s",
            database_url,
            e
        )
    
    return database_url


# Database URL from environment variable
_raw_database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://pm_user:pm_password@localhost:5432/project_management"
)

# Convert localhost URLs to Docker service names when running in containers
DATABASE_URL = _convert_localhost_to_docker_service(_raw_database_url)

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
    # Import all models to ensure they're registered with Base
    from database.orm_models import Base  # noqa: F401
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except (ConnectionError, OSError, RuntimeError) as e:
        logger.warning("Database initialization warning: %s", e)


def close_db():
    """Close database connections"""
    engine.dispose()

