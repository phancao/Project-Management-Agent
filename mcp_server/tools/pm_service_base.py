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
    
    async def __call__(self, **kwargs) -> dict[str, Any]:
        """Make tool callable."""
        return await self.execute(**kwargs)


class PMServiceReadTool(PMServiceTool):
    """Base class for read-only PM Service tools."""
    pass


class PMServiceWriteTool(PMServiceTool):
    """Base class for write PM Service tools."""
    pass

