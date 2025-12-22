"""
Configuration for MCP Meeting Server.
"""

from dataclasses import dataclass
import os


@dataclass
class MeetingServerConfig:
    """
    Configuration for the Meeting MCP Server.
    """
    # Server info
    server_name: str = "meeting-server"
    version: str = "1.0.0"
    
    # Network
    host: str = "0.0.0.0"
    port: int = 8082
    
    # Transport
    transport: str = "sse"  # stdio, sse, http
    
    # Authentication
    enable_auth: bool = True
    api_key_header: str = "X-MCP-API-Key"
    
    # Database
    database_url: str = "sqlite:///./data/meeting_mcp.db"
    
    # Upload settings
    upload_dir: str = "./uploads/meetings"
    max_upload_size_mb: int = 500
    
    # Logging
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> "MeetingServerConfig":
        """Load configuration from environment variables"""
        return cls(
            server_name=os.getenv("MEETING_SERVER_NAME", "meeting-server"),
            host=os.getenv("MEETING_SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("MEETING_SERVER_PORT", "8082")),
            transport=os.getenv("MEETING_SERVER_TRANSPORT", "sse"),
            enable_auth=os.getenv("MEETING_SERVER_AUTH", "true").lower() == "true",
            database_url=os.getenv("MEETING_DATABASE_URL", "sqlite:///./data/meeting_mcp.db"),
            upload_dir=os.getenv("MEETING_UPLOAD_DIR", "./uploads/meetings"),
            max_upload_size_mb=int(os.getenv("MEETING_MAX_UPLOAD_MB", "500")),
            log_level=os.getenv("MEETING_LOG_LEVEL", "INFO"),
        )
