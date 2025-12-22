"""
Shared MCP Tools Package

This package provides base classes and utilities for MCP tools
that can be used by both PM MCP Server and Meeting Notes MCP Server.
"""

from shared.mcp_tools.base import (
    BaseTool,
    ReadTool,
    WriteTool,
    AnalyticsTool,
    ToolResult,
)
from shared.mcp_tools.decorators import (
    mcp_tool,
    require_project,
    default_value,
)

__all__ = [
    # Base classes
    'BaseTool',
    'ReadTool',
    'WriteTool',
    'AnalyticsTool',
    'ToolResult',
    # Decorators
    'mcp_tool',
    'require_project',
    'default_value',
]
