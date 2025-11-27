"""
Base Tool Classes

Abstract base classes for all MCP tools.
Provides common functionality and consistent patterns.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from mcp.types import TextContent

from ..core.tool_context import ToolContext

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """
    Base class for all MCP tools.
    
    Provides:
    - Consistent error handling
    - Automatic logging
    - Response formatting
    - Access to tool context
    
    Subclasses must implement:
    - execute(**kwargs): Tool-specific logic
    """
    
    def __init__(self, context: ToolContext):
        """
        Initialize base tool.
        
        Args:
            context: Tool context with access to managers and services
        """
        self.context = context
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Execute the tool.
        
        This method must be implemented by subclasses.
        
        Args:
            **kwargs: Tool-specific arguments
        
        Returns:
            Tool-specific result (will be formatted as JSON)
        """
        pass
    
    async def __call__(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        MCP tool entry point.
        
        This is called by the MCP server when the tool is invoked.
        
        Handles:
        - Argument validation
        - Logging
        - Error handling
        - Response formatting
        
        Args:
            arguments: Tool arguments from MCP request
        
        Returns:
            List of TextContent responses
        """
        tool_name = self.__class__.__name__
        
        try:
            # Log invocation
            logger.info(
                "[%s] Called with arguments: %s",
                tool_name,
                self._sanitize_args_for_log(arguments)
            )
            
            # Execute tool
            result = await self.execute(**arguments)
            
            # Format response
            response = self._format_response(result)
            
            # Log success
            logger.info("[%s] Completed successfully", tool_name)
            
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            # Log error
            logger.error(
                "[%s] Error: %s",
                tool_name,
                str(e),
                exc_info=True
            )
            
            # Return error response
            error_message = self._format_error(e)
            return [TextContent(type="text", text=error_message)]
    
    def _format_response(self, result: Any) -> str:
        """
        Format result as JSON string.
        
        Args:
            result: Tool result
        
        Returns:
            JSON string
        """
        return json.dumps(result, indent=2, default=str)
    
    def _format_error(self, error: Exception) -> str:
        """
        Format error as JSON string.
        
        Args:
            error: Exception that occurred
        
        Returns:
            JSON error message
        """
        return json.dumps({
            "error": str(error),
            "type": type(error).__name__
        }, indent=2)
    
    def _sanitize_args_for_log(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize arguments for logging (hide sensitive data).
        
        Args:
            arguments: Tool arguments
        
        Returns:
            Sanitized arguments
        """
        # Create a copy to avoid modifying original
        sanitized = arguments.copy()
        
        # Hide sensitive fields
        sensitive_fields = ["password", "api_key", "api_token", "token", "secret"]
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = "***REDACTED***"
        
        return sanitized


class ReadTool(BaseTool):
    """
    Base class for read-only tools.
    
    Read tools:
    - Don't modify data
    - Can be cached
    - Are safe to retry
    
    Examples: list_projects, get_task, list_sprints
    """
    
    pass


class WriteTool(BaseTool):
    """
    Base class for write tools.
    
    Write tools:
    - Modify data
    - Should not be cached
    - May not be safe to retry
    
    Examples: create_task, update_project, delete_sprint
    """
    
    pass


class AnalyticsTool(BaseTool):
    """
    Base class for analytics tools.
    
    Analytics tools:
    - Use analytics manager
    - May be computationally expensive
    - Results can be cached
    
    Examples: burndown_chart, velocity_chart, sprint_report
    """
    
    async def get_analytics_service(self, project_id: str):
        """
        Get analytics service from context.
        
        Convenience method for analytics tools.
        
        Args:
            project_id: Project ID
        
        Returns:
            Tuple of (AnalyticsService, actual_project_id)
        """
        return await self.context.analytics_manager.get_service(project_id)


class ProviderConfigTool(BaseTool):
    """
    Base class for provider configuration tools.
    
    Provider config tools:
    - Manage provider connections
    - Handle credentials
    - May require special permissions
    
    Examples: list_providers, configure_provider, test_connection
    """
    
    pass


