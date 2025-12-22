"""
Base classes for MCP tools.

These base classes provide a consistent interface for implementing
MCP (Model Context Protocol) tools across different servers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, TypeVar
from enum import Enum


class ToolCategory(str, Enum):
    """Category of MCP tool for classification"""
    READ = "read"          # Read-only operations
    WRITE = "write"        # Write operations
    ANALYTICS = "analytics"  # Analytics/charts
    CONFIG = "config"      # Configuration
    UTILITY = "utility"    # Utility operations


@dataclass
class ToolResult:
    """
    Standard result type for MCP tool execution.
    
    Provides a consistent response format for all tools.
    """
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def ok(cls, data: Any, **metadata) -> "ToolResult":
        """Create a successful result"""
        return cls(success=True, data=data, metadata=metadata)
    
    @classmethod
    def fail(cls, error: str, **metadata) -> "ToolResult":
        """Create a failed result"""
        return cls(success=False, error=error, metadata=metadata)
    
    def to_mcp_response(self) -> List[Dict[str, Any]]:
        """Convert to MCP response format"""
        if self.success:
            import json
            content = json.dumps(self.data) if isinstance(self.data, (dict, list)) else str(self.data)
            return [{"type": "text", "text": content}]
        else:
            return [{"type": "text", "text": f"Error: {self.error}"}]


# Type variable for context
ContextT = TypeVar('ContextT')


class BaseTool(ABC, Generic[ContextT]):
    """
    Abstract base class for all MCP tools.
    
    Tools implement the execute method and declare their schema
    via the @mcp_tool decorator.
    """
    
    def __init__(self, context: ContextT):
        """
        Initialize tool with context.
        
        Args:
            context: The tool context (provides access to services)
        """
        self._context = context
    
    @property
    def context(self) -> ContextT:
        """Get the tool context"""
        return self._context
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for MCP registration"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM"""
        pass
    
    @property
    def category(self) -> ToolCategory:
        """Tool category (default: UTILITY)"""
        return ToolCategory.UTILITY
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool operation.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with operation outcome
        """
        pass
    
    def validate_params(self, **kwargs) -> Optional[str]:
        """
        Validate input parameters.
        
        Override to add custom validation.
        
        Returns:
            Error message if validation fails, None if valid
        """
        return None
    
    async def run(self, **kwargs) -> ToolResult:
        """
        Run the tool with validation.
        
        This is the main entry point that validates then executes.
        """
        error = self.validate_params(**kwargs)
        if error:
            return ToolResult.fail(error)
        
        try:
            return await self.execute(**kwargs)
        except Exception as e:
            return ToolResult.fail(f"Tool execution failed: {str(e)}")


class ReadTool(BaseTool[ContextT], Generic[ContextT]):
    """
    Base class for read-only tools.
    
    Read tools fetch data without modifying state.
    """
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.READ


class WriteTool(BaseTool[ContextT], Generic[ContextT]):
    """
    Base class for write tools.
    
    Write tools modify state (create, update, delete).
    """
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.WRITE
    
    def get_confirmation_message(self, **kwargs) -> Optional[str]:
        """
        Get a confirmation message for dangerous operations.
        
        Override to return a message that requires user confirmation.
        Return None if no confirmation needed.
        """
        return None


class AnalyticsTool(BaseTool[ContextT], Generic[ContextT]):
    """
    Base class for analytics tools.
    
    Analytics tools generate charts, reports, and metrics.
    """
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.ANALYTICS
    
    def get_cache_key(self, **kwargs) -> Optional[str]:
        """
        Get a cache key for the result.
        
        Override to enable caching of analytics results.
        Return None to disable caching.
        """
        return None
    
    def get_cache_ttl(self) -> int:
        """Get cache TTL in seconds (default 5 minutes)"""
        return 300


class ConfigTool(BaseTool[ContextT], Generic[ContextT]):
    """
    Base class for configuration tools.
    
    Config tools manage settings and configurations.
    """
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CONFIG
