"""
PM MCP Server

A standalone MCP (Model Context Protocol) server that exposes Project Management
operations as tools for AI agents.

Features:
- Multi-provider support (OpenProject, JIRA, ClickUp, Internal DB)
- 50+ PM tools (projects, tasks, sprints, epics, users, analytics)
- Multiple transports (stdio, SSE, HTTP)
- Authentication and authorization
- Audit logging

Usage:
    # Run with stdio transport (for Claude Desktop, etc.)
    python scripts/run_pm_mcp_server.py --transport stdio
    
    # Run with SSE transport (for web agents)
    python scripts/run_pm_mcp_server.py --transport sse --port 8080
    
    # Run with HTTP transport
    python scripts/run_pm_mcp_server.py --transport http --port 8080
"""

from .server import PMMCPServer
from .config import PMServerConfig

__all__ = ["PMMCPServer", "PMServerConfig"]
__version__ = "0.1.0"

