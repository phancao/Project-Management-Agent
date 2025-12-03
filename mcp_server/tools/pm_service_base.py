# PM Service Base Tool
"""
Base class for MCP tools that use PM Service client.
"""

import logging
import os
from typing import Any, Optional

from pm_service.client import AsyncPMServiceClient

logger = logging.getLogger(__name__)

# PM Service URL - defaults to Docker service name
PM_SERVICE_URL = os.environ.get("PM_SERVICE_URL", "http://pm_service:8001")


class PMServiceTool:
    """
    Base class for MCP tools that use PM Service.
    
    Provides access to PM Service client for making API calls.
    """
    
    def __init__(self, context=None):
        """
        Initialize tool with optional context.
        
        Args:
            context: Tool context (for backward compatibility)
        """
        self.context = context
        self._client: Optional[AsyncPMServiceClient] = None
    
    @property
    def client(self) -> AsyncPMServiceClient:
        """Get PM Service client."""
        if self._client is None:
            self._client = AsyncPMServiceClient(base_url=PM_SERVICE_URL)
        return self._client
    
    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute the tool. Override in subclass."""
        raise NotImplementedError("Subclass must implement execute()")
    
    async def __call__(self, arguments: dict[str, Any] = None) -> dict[str, Any]:
        """
        MCP tool entry point.
        
        Args:
            arguments: Tool arguments from MCP request (dict)
        
        Returns:
            Tool result (dict)
        
        Raises:
            PermissionError: If permission is denied (will be passed to agent)
        """
        try:
            if arguments:
                return await self.execute(**arguments)
            else:
                return await self.execute()
        except PermissionError:
            # Re-raise permission errors so agent can inform the user
            raise
        except Exception as e:
            # Check if error message contains permission-related keywords
            error_msg = str(e)
            if "403" in error_msg or "Forbidden" in error_msg or "permission" in error_msg.lower():
                raise PermissionError(
                    f"Permission denied: {error_msg}. "
                    "Please check your API token permissions or contact your administrator."
                ) from e
            raise


class PMServiceReadTool(PMServiceTool):
    """Base class for read-only PM Service tools."""
    pass


class PMServiceWriteTool(PMServiceTool):
    """Base class for write PM Service tools."""
    pass

