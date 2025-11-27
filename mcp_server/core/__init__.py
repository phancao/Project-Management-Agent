"""
Core Business Logic Layer

This module contains the core business logic for the MCP server,
separated from protocol handling and transport layers.

Components:
- ProviderManager: Manages PM provider lifecycle and instances
- AnalyticsManager: Integrates analytics service with providers
- ToolContext: Shared context for all tools
- AuthManager: Handles API key validation and management
"""

from .provider_manager import ProviderManager
from .analytics_manager import AnalyticsManager
from .tool_context import ToolContext
from .auth_manager import AuthManager

__all__ = [
    "ProviderManager",
    "AnalyticsManager",
    "ToolContext",
    "AuthManager",
]


