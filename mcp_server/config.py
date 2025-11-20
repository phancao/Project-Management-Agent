"""
PM MCP Server Configuration

Manages server configuration, including database connection,
transport settings, authentication, and logging.
"""

import os
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class PMServerConfig:
    """Configuration for PM MCP Server."""
    
    # Server identity
    server_name: str = "pm-server"
    server_version: str = "0.1.0"
    
    # Database
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/pm_agent"
        )
    )
    
    # Transport
    transport: Literal["stdio", "sse", "http"] = "stdio"
    host: str = "localhost"
    port: int = 8080
    
    # Authentication
    enable_auth: bool = False
    auth_token_secret: str = field(
        default_factory=lambda: os.getenv("MCP_AUTH_SECRET", "")
    )
    
    # Authorization
    enable_rbac: bool = False
    
    # Audit logging
    enable_audit_log: bool = True
    audit_log_file: str = "logs/pm_mcp_audit.log"
    
    # Performance
    cache_ttl: int = 300  # 5 minutes
    max_concurrent_requests: int = 100
    request_timeout: int = 30  # seconds
    
    # Logging
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )
    log_file: str = "logs/pm_mcp_server.log"
    
    # Tool filtering (for agent-specific tool access)
    enabled_tools: list[str] | None = None  # None = all tools enabled
    
    @classmethod
    def from_env(cls) -> "PMServerConfig":
        """Create config from environment variables."""
        default_db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/pm_agent"
        )
        return cls(
            server_name=os.getenv("MCP_SERVER_NAME", "pm-server"),
            database_url=os.getenv("DATABASE_URL", default_db_url),
            transport=os.getenv("MCP_TRANSPORT", "stdio"),
            host=os.getenv("MCP_HOST", "localhost"),
            port=int(os.getenv("MCP_PORT", "8080")),
            enable_auth=os.getenv("MCP_ENABLE_AUTH", "false").lower() == "true",
            enable_rbac=os.getenv("MCP_ENABLE_RBAC", "false").lower() == "true",
            enable_audit_log=os.getenv("MCP_ENABLE_AUDIT", "true").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
    
    def validate(self) -> None:
        """Validate configuration."""
        if self.enable_auth and not self.auth_token_secret:
            raise ValueError("AUTH_TOKEN_SECRET must be set when authentication is enabled")
        
        if self.transport in ["sse", "http"] and not (1024 <= self.port <= 65535):
            raise ValueError(f"Invalid port: {self.port}. Must be between 1024 and 65535")
        
        if self.cache_ttl < 0:
            raise ValueError("cache_ttl must be non-negative")

