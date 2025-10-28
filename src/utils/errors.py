"""
Error handling system for Project Management Agent
Provides custom exceptions, error decorators, and centralized error management
"""

import functools
import traceback
from typing import Any, Callable, Dict, Optional, Type
from enum import Enum


class ErrorCode(Enum):
    """Error codes for different types of errors"""
    AUTHENTICATION_ERROR = "AUTH_001"
    AUTHORIZATION_ERROR = "AUTH_002"
    VALIDATION_ERROR = "VAL_001"
    CONFIGURATION_ERROR = "CONFIG_001"
    DATABASE_ERROR = "DB_001"
    API_ERROR = "API_001"
    LLM_ERROR = "LLM_001"
    SEARCH_ERROR = "SEARCH_001"
    CONVERSATION_ERROR = "CONV_001"
    UNKNOWN_ERROR = "UNKNOWN_001"


class ProjectManagementError(Exception):
    """Base exception for Project Management Agent"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary"""
        return {
            'error_code': self.error_code.value,
            'message': self.message,
            'details': self.details
        }


class AuthenticationError(ProjectManagementError):
    """Authentication related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCode.AUTHENTICATION_ERROR, details)


class AuthorizationError(ProjectManagementError):
    """Authorization related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCode.AUTHORIZATION_ERROR, details)


class ValidationError(ProjectManagementError):
    """Validation related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCode.VALIDATION_ERROR, details)


class ConfigurationError(ProjectManagementError):
    """Configuration related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCode.CONFIGURATION_ERROR, details)


class DatabaseError(ProjectManagementError):
    """Database related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCode.DATABASE_ERROR, details)


class APIError(ProjectManagementError):
    """API related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCode.API_ERROR, details)


class LLMError(ProjectManagementError):
    """LLM related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCode.LLM_ERROR, details)


class SearchError(ProjectManagementError):
    """Search related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCode.SEARCH_ERROR, details)


class ConversationError(ProjectManagementError):
    """Conversation flow related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCode.CONVERSATION_ERROR, details)


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise APIError("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.timeout
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


def handle_errors(
    error_types: Optional[Dict[Type[Exception], Callable]] = None,
    default_handler: Optional[Callable] = None,
    reraise: bool = True
):
    """
    Decorator to handle errors with custom handlers
    
    Args:
        error_types: Dictionary mapping exception types to handlers
        default_handler: Default handler for unhandled exceptions
        reraise: Whether to reraise the exception after handling
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Check for specific error handlers
                if error_types:
                    for exc_type, handler in error_types.items():
                        if isinstance(e, exc_type):
                            handler(e)
                            if not reraise:
                                return None
                            break
                    else:
                        # No specific handler found
                        if default_handler:
                            default_handler(e)
                            if not reraise:
                                return None
                
                # Reraise if requested
                if reraise:
                    raise
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Check for specific error handlers
                if error_types:
                    for exc_type, handler in error_types.items():
                        if isinstance(e, exc_type):
                            handler(e)
                            if not reraise:
                                return None
                            break
                    else:
                        # No specific handler found
                        if default_handler:
                            default_handler(e)
                            if not reraise:
                                return None
                
                # Reraise if requested
                if reraise:
                    raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def error_handler(error: Exception) -> Dict[str, Any]:
    """
    Centralized error handler that converts exceptions to standardized format
    
    Args:
        error: Exception to handle
    
    Returns:
        Dictionary with error information
    """
    if isinstance(error, ProjectManagementError):
        return {
            'error': True,
            'error_code': error.error_code.value,
            'message': error.message,
            'details': error.details,
            'type': error.__class__.__name__
        }
    else:
        return {
            'error': True,
            'error_code': ErrorCode.UNKNOWN_ERROR.value,
            'message': str(error),
            'details': {
                'traceback': traceback.format_exc()
            },
            'type': error.__class__.__name__
        }


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None):
    """Log error with context information"""
    error_info = error_handler(error)
    if context:
        error_info['context'] = context
    
    print(f"❌ Error: {error_info['message']}")
    print(f"   Code: {error_info['error_code']}")
    print(f"   Type: {error_info['type']}")
    if error_info.get('details'):
        print(f"   Details: {error_info['details']}")


# Import required modules
import time
import asyncio


