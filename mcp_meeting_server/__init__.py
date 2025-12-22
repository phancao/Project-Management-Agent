"""
MCP Meeting Server Package

An MCP (Model Context Protocol) server that exposes meeting processing
capabilities as tools for AI agents.
"""

from mcp_meeting_server.server import MeetingMCPServer
from mcp_meeting_server.config import MeetingServerConfig

__all__ = [
    'MeetingMCPServer',
    'MeetingServerConfig',
]
