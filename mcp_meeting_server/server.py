"""
MCP Meeting Server - Main server implementation.

Provides an MCP server that exposes meeting processing tools
for AI agents to use.
"""

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from mcp_meeting_server.config import MeetingServerConfig

logger = logging.getLogger(__name__)


class MeetingMCPServer:
    """
    MCP Server for meeting processing tools.
    
    Exposes meeting processing capabilities as MCP tools that can be
    used by AI agents via various transports (stdio, SSE, HTTP).
    """
    
    def __init__(
        self,
        config: Optional[MeetingServerConfig] = None,
        user_id: Optional[str] = None,
    ):
        """
        Initialize the Meeting MCP Server.
        
        Args:
            config: Server configuration
            user_id: Optional user ID for user-scoped operations
        """
        self.config = config or MeetingServerConfig()
        self.user_id = user_id
        self._server = None
        self._tool_context = None
        
        # Ensure directories exist
        Path(self.config.upload_dir).mkdir(parents=True, exist_ok=True)
    
    def _initialize_mcp_server(self):
        """Initialize the underlying MCP server"""
        try:
            from mcp.server import Server
            
            # Initialize database
            try:
                from database.connection import init_db
                init_db()
                logger.info("Database initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                # We don't raise here to allow server to start, but tools might fail
            
            self._server = Server(self.config.server_name)
            self._register_tools()
            
        except ImportError:
            raise ImportError("MCP SDK not installed. Run: pip install mcp")
    
    def _register_tools(self):
        """Register all meeting tools with the server"""
        if not self._server:
            return
        
        # Import and register tools
        from mcp_meeting_server.tools import register_all_tools
        register_all_tools(self._server, self)
    
    async def run(self):
        """Run the server with configured transport"""
        self._initialize_mcp_server()
        
        if self.config.transport == "stdio":
            await self._run_stdio()
        elif self.config.transport == "sse":
            await self._run_sse()
        elif self.config.transport == "http":
            await self._run_http()
        else:
            raise ValueError(f"Unknown transport: {self.config.transport}")
    
    async def _run_stdio(self):
        """Run with stdio transport (for Claude Desktop)"""
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            await self._server.run(
                read_stream,
                write_stream,
                self._server.create_initialization_options()
            )
    
    async def _run_sse(self):
        """Run with SSE transport"""
        from mcp_meeting_server.transports.sse import create_sse_app
        import uvicorn
        
        app = create_sse_app(self)
        
        config = uvicorn.Config(
            app,
            host=self.config.host,
            port=self.config.port,
            log_level=self.config.log_level.lower(),
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    async def _run_http(self):
        """Run with HTTP transport"""
        from mcp_meeting_server.transports.http import create_http_app
        import uvicorn
        
        app = create_http_app(self)
        
        config = uvicorn.Config(
            app,
            host=self.config.host,
            port=self.config.port,
            log_level=self.config.log_level.lower(),
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    # Service accessors for tools
    def get_meeting_handler(self):
        """Get the meeting handler for processing"""
        from meeting_agent.handlers import MeetingHandler
        from meeting_agent.config import MeetingAgentConfig
        
        config = MeetingAgentConfig(
            upload_dir=self.config.upload_dir,
        )
        return MeetingHandler(config=config)
    
    def get_db_session(self):
        """Get a database session"""
        from database.connection import SessionLocal
        return SessionLocal()
        
    def get_upload_dir(self) -> Path:
        """Get the upload directory path"""
        return Path(self.config.upload_dir)


def run_server(config: Optional[MeetingServerConfig] = None):
    """
    Run the Meeting MCP Server.
    
    Entry point for running the server.
    """
    import asyncio
    
    server_config = config or MeetingServerConfig.from_env()
    server = MeetingMCPServer(config=server_config)
    
    logger.info(f"Starting Meeting MCP Server on {server_config.host}:{server_config.port}")
    logger.info(f"Transport: {server_config.transport}")
    
    asyncio.run(server.run())
