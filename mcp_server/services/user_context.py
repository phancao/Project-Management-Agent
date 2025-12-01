"""
User Context Service

Manages user-scoped MCP server instances and context.
"""

import logging
from typing import Optional

from ..server import PMMCPServer
from ..config import PMServerConfig

logger = logging.getLogger(__name__)


class UserContext:
    """Manages user-scoped server instances and context."""
    
    @staticmethod
    def create_user_scoped_server(
        user_id: str,
        config: Optional[PMServerConfig] = None
    ) -> PMMCPServer:
        """
        Create a user-scoped MCP server instance.
        
        This ensures that the server only has access to providers
        where created_by = user_id, providing proper credential isolation.
        
        Args:
            user_id: User UUID string
            config: Server configuration (optional, loads from env if not provided)
            
        Returns:
            Configured PMMCPServer instance with user context
        """
        if not user_id:
            raise ValueError("user_id is required for user-scoped server")
        
        logger.info(f"[UserContext] Creating user-scoped MCP server for user: {user_id}")
        
        # Use provided config or load from environment
        server_config = config or PMServerConfig.from_env()
        
        # Create server with user context
        mcp_server = PMMCPServer(config=server_config, user_id=user_id)
        
        # Initialize Tool Context with user context
        mcp_server._initialize_tool_context()
        
        # Register tools
        mcp_server._register_all_tools()
        
        logger.info(f"[UserContext] User-scoped MCP server initialized for user: {user_id}")
        
        return mcp_server

