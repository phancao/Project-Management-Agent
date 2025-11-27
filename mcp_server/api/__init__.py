"""
MCP Server API Module

This module contains REST API endpoints for the MCP Server,
separate from the MCP protocol endpoints.
"""

from .provider_sync import router as provider_sync_router

__all__ = ["provider_sync_router"]



