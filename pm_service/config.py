# PM Service Configuration
"""
Configuration management for PM Service.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """PM Service settings."""
    
    # Service settings
    service_name: str = "PM Service"
    service_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8001
    
    # Database settings
    database_url: str = "postgresql://mcp_user:mcp_password@localhost:5435/mcp_server"
    
    # External PM providers
    openproject_url: str = "http://localhost:8083"
    
    # Performance settings
    request_timeout: int = 30  # seconds
    max_connections: int = 100
    
    # Cache settings (optional Redis)
    redis_url: str | None = None
    cache_ttl: int = 300  # 5 minutes
    
    class Config:
        env_prefix = "PM_SERVICE_"
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

