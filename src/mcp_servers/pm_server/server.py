"""
PM MCP Server Implementation

Main server class that registers PM tools and handles MCP protocol communication.
"""

import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from sqlalchemy.orm import Session

from database.connection import get_db_session
from src.server.pm_handler import PMHandler
from .config import PMServerConfig
from .tools import (
    register_project_tools,
    register_task_tools,
    register_sprint_tools,
    register_epic_tools,
    register_user_tools,
    register_analytics_tools,
)

logger = logging.getLogger(__name__)


class PMMCPServer:
    """
    PM MCP Server
    
    Exposes Project Management operations as MCP tools for AI agents.
    Supports multiple PM providers (OpenProject, JIRA, ClickUp, Internal DB).
    """
    
    def __init__(self, config: PMServerConfig | None = None):
        """
        Initialize PM MCP Server.
        
        Args:
            config: Server configuration. If None, loads from environment.
        """
        self.config = config or PMServerConfig.from_env()
        self.config.validate()
        
        # Initialize MCP server
        self.server = Server(self.config.server_name)
        
        # Database session
        self.db_session: Session | None = None
        
        # PM Handler (will be initialized when server starts)
        self.pm_handler: PMHandler | None = None
        
        # Tool registry
        self.registered_tools: list[str] = []
        
        logger.info(
            f"PM MCP Server initialized: {self.config.server_name} v{self.config.server_version}"
        )
    
    def _initialize_pm_handler(self) -> None:
        """Initialize PM Handler with database session."""
        if self.pm_handler is not None:
            return
        
        logger.info("Initializing PM Handler...")
        
        # Get database session
        self.db_session = next(get_db_session())
        
        # Initialize PMHandler in multi-provider mode
        self.pm_handler = PMHandler.from_db_session(self.db_session)
        
        # Get provider count
        provider_count = len(self.pm_handler._get_active_providers())
        
        logger.info(
            f"PM Handler initialized with {provider_count} active providers"
        )
    
    def _register_all_tools(self) -> None:
        """Register all PM tools with the MCP server."""
        if self.pm_handler is None:
            raise RuntimeError("PM Handler not initialized. Call _initialize_pm_handler first.")
        
        logger.info("Registering PM tools...")
        
        # Register tools from each module
        tool_modules = [
            ("projects", register_project_tools),
            ("tasks", register_task_tools),
            ("sprints", register_sprint_tools),
            ("epics", register_epic_tools),
            ("users", register_user_tools),
            ("analytics", register_analytics_tools),
        ]
        
        for module_name, register_func in tool_modules:
            try:
                count = register_func(self.server, self.pm_handler, self.config)
                self.registered_tools.extend([f"{module_name}.*"])
                logger.info(f"Registered {count} {module_name} tools")
            except Exception as e:
                logger.error(f"Failed to register {module_name} tools: {e}")
                raise
        
        logger.info(f"Total tools registered: {len(self.registered_tools)}")
    
    async def run_stdio(self) -> None:
        """
        Run server with stdio transport.
        
        This is the standard transport for Claude Desktop and similar clients.
        """
        logger.info("Starting PM MCP Server with stdio transport...")
        
        try:
            # Initialize PM Handler
            self._initialize_pm_handler()
            
            # Register all tools
            self._register_all_tools()
            
            # Run server with stdio
            async with stdio_server() as (read_stream, write_stream):
                logger.info("PM MCP Server running on stdio")
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        except Exception as e:
            logger.error(f"Error running PM MCP Server: {e}")
            raise
        finally:
            self._cleanup()
    
    async def run_sse(self) -> None:
        """
        Run server with SSE (Server-Sent Events) transport.
        
        This transport is suitable for web-based agents.
        """
        logger.info(
            f"Starting PM MCP Server with SSE transport on {self.config.host}:{self.config.port}..."
        )
        
        try:
            # Initialize PM Handler
            self._initialize_pm_handler()
            
            # Register all tools
            self._register_all_tools()
            
            # TODO: Implement SSE transport
            # This will require creating an SSE endpoint similar to the one in src/server/app.py
            logger.warning("SSE transport not yet implemented")
            raise NotImplementedError("SSE transport coming soon")
        except Exception as e:
            logger.error(f"Error running PM MCP Server: {e}")
            raise
        finally:
            self._cleanup()
    
    async def run_http(self) -> None:
        """
        Run server with HTTP transport.
        
        This transport provides RESTful API access to MCP tools.
        """
        logger.info(
            f"Starting PM MCP Server with HTTP transport on {self.config.host}:{self.config.port}..."
        )
        
        try:
            # Initialize PM Handler
            self._initialize_pm_handler()
            
            # Register all tools
            self._register_all_tools()
            
            # TODO: Implement HTTP transport
            logger.warning("HTTP transport not yet implemented")
            raise NotImplementedError("HTTP transport coming soon")
        except Exception as e:
            logger.error(f"Error running PM MCP Server: {e}")
            raise
        finally:
            self._cleanup()
    
    def _cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up PM MCP Server...")
        
        if self.db_session:
            self.db_session.close()
            self.db_session = None
        
        self.pm_handler = None
        
        logger.info("PM MCP Server stopped")
    
    async def run(self) -> None:
        """
        Run server with configured transport.
        
        This is the main entry point that dispatches to the appropriate transport.
        """
        if self.config.transport == "stdio":
            await self.run_stdio()
        elif self.config.transport == "sse":
            await self.run_sse()
        elif self.config.transport == "http":
            await self.run_http()
        else:
            raise ValueError(f"Unknown transport: {self.config.transport}")

