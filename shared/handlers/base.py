"""
Base handler classes and common types.

These provide a consistent interface for all handlers across agents.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from datetime import datetime


class HandlerStatus(str, Enum):
    """Handler execution status"""
    SUCCESS = "success"
    PARTIAL = "partial"  # Some operations succeeded
    FAILED = "failed"
    PENDING = "pending"
    CANCELLED = "cancelled"


@dataclass
class HandlerContext:
    """
    Context passed to handlers during execution.
    
    Contains common data needed by handlers.
    """
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    sprint_id: Optional[str] = None
    locale: str = "en-US"
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def with_project(self, project_id: str) -> "HandlerContext":
        """Create a new context with the specified project"""
        return HandlerContext(
            user_id=self.user_id,
            project_id=project_id,
            sprint_id=self.sprint_id,
            locale=self.locale,
            request_id=self.request_id,
            timestamp=self.timestamp,
            metadata=self.metadata.copy(),
        )
    
    def with_sprint(self, sprint_id: str) -> "HandlerContext":
        """Create a new context with the specified sprint"""
        return HandlerContext(
            user_id=self.user_id,
            project_id=self.project_id,
            sprint_id=sprint_id,
            locale=self.locale,
            request_id=self.request_id,
            timestamp=self.timestamp,
            metadata=self.metadata.copy(),
        )


# Type variable for handler result data
T = TypeVar('T')


@dataclass
class HandlerResult(Generic[T]):
    """
    Standard result type for handler operations.
    
    Provides consistent error handling and metadata across all handlers.
    """
    status: HandlerStatus
    data: Optional[T] = None
    message: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        """Check if the operation was successful"""
        return self.status in (HandlerStatus.SUCCESS, HandlerStatus.PARTIAL)
    
    @property
    def is_failed(self) -> bool:
        """Check if the operation failed"""
        return self.status == HandlerStatus.FAILED
    
    @classmethod
    def success(cls, data: T, message: Optional[str] = None, **metadata) -> "HandlerResult[T]":
        """Create a successful result"""
        return cls(
            status=HandlerStatus.SUCCESS,
            data=data,
            message=message,
            metadata=metadata,
        )
    
    @classmethod
    def failure(cls, message: str, errors: Optional[List[str]] = None, **metadata) -> "HandlerResult[T]":
        """Create a failed result"""
        return cls(
            status=HandlerStatus.FAILED,
            message=message,
            errors=errors or [message],
            metadata=metadata,
        )
    
    @classmethod
    def partial(cls, data: T, warnings: List[str], message: Optional[str] = None, **metadata) -> "HandlerResult[T]":
        """Create a partial success result"""
        return cls(
            status=HandlerStatus.PARTIAL,
            data=data,
            message=message,
            warnings=warnings,
            metadata=metadata,
        )


class BaseHandler(ABC, Generic[T]):
    """
    Abstract base class for all handlers.
    
    Handlers encapsulate complex business operations and provide
    a consistent interface for execution.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Handler name for logging and identification"""
        pass
    
    @abstractmethod
    async def execute(self, context: HandlerContext, **kwargs) -> HandlerResult[T]:
        """
        Execute the handler's main operation.
        
        Args:
            context: Handler context with common data
            **kwargs: Operation-specific parameters
            
        Returns:
            HandlerResult with the operation outcome
        """
        pass
    
    async def validate(self, context: HandlerContext, **kwargs) -> Optional[str]:
        """
        Validate inputs before execution.
        
        Override to add validation logic.
        
        Returns:
            Error message if validation fails, None if valid
        """
        return None
    
    async def pre_execute(self, context: HandlerContext, **kwargs) -> None:
        """Hook called before execution. Override for setup logic."""
        pass
    
    async def post_execute(self, context: HandlerContext, result: HandlerResult[T], **kwargs) -> None:
        """Hook called after execution. Override for cleanup logic."""
        pass
    
    async def run(self, context: HandlerContext, **kwargs) -> HandlerResult[T]:
        """
        Run the handler with validation and hooks.
        
        This is the main entry point that calls validate, pre_execute,
        execute, and post_execute in order.
        """
        # Validate first
        error = await self.validate(context, **kwargs)
        if error:
            return HandlerResult.failure(error)
        
        try:
            # Pre-execution hook
            await self.pre_execute(context, **kwargs)
            
            # Main execution
            result = await self.execute(context, **kwargs)
            
            # Post-execution hook
            await self.post_execute(context, result, **kwargs)
            
            return result
            
        except Exception as e:
            return HandlerResult.failure(
                f"Handler {self.name} failed: {str(e)}",
                errors=[str(e)],
            )
