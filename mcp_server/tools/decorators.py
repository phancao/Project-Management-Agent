"""
Tool Decorators

Decorators for MCP tool registration and validation.
"""

import logging
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)


def mcp_tool(name: str, description: str, input_schema: dict[str, Any] | None = None):
    """
    Decorator for MCP tool registration.
    
    Adds metadata to tool class for registration with MCP server.
    
    Usage:
        @mcp_tool(
            name="my_tool",
            description="My tool description",
            input_schema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "Parameter 1"}
                },
                "required": ["param1"]
            }
        )
        class MyTool(BaseTool):
            async def execute(self, param1: str):
                ...
    
    Args:
        name: Tool name (must be unique)
        description: Tool description for AI agents
        input_schema: JSON schema for tool input (optional)
    
    Returns:
        Decorated class
    """
    def decorator(cls):
        cls._mcp_name = name
        cls._mcp_description = description
        cls._mcp_input_schema = input_schema or {
            "type": "object",
            "properties": {},
            "additionalProperties": True
        }
        return cls
    return decorator


def require_project(func: Callable) -> Callable:
    """
    Decorator to require project_id argument.
    
    Usage:
        @require_project
        async def execute(self, project_id: str, **kwargs):
            ...
    
    Args:
        func: Function to decorate
    
    Returns:
        Decorated function
    """
    @wraps(func)
    async def wrapper(self, **kwargs):
        if "project_id" not in kwargs or not kwargs["project_id"]:
            raise ValueError("project_id is required")
        return await func(self, **kwargs)
    return wrapper


def require_provider(func: Callable) -> Callable:
    """
    Decorator to require provider_id argument.
    
    Usage:
        @require_provider
        async def execute(self, provider_id: str, **kwargs):
            ...
    
    Args:
        func: Function to decorate
    
    Returns:
        Decorated function
    """
    @wraps(func)
    async def wrapper(self, **kwargs):
        if "provider_id" not in kwargs or not kwargs["provider_id"]:
            raise ValueError("provider_id is required")
        return await func(self, **kwargs)
    return wrapper


def require_sprint(func: Callable) -> Callable:
    """
    Decorator to require sprint_id argument.
    
    Usage:
        @require_sprint
        async def execute(self, sprint_id: str, **kwargs):
            ...
    
    Args:
        func: Function to decorate
    
    Returns:
        Decorated function
    """
    @wraps(func)
    async def wrapper(self, **kwargs):
        if "sprint_id" not in kwargs or not kwargs["sprint_id"]:
            raise ValueError("sprint_id is required")
        return await func(self, **kwargs)
    return wrapper


def require_task(func: Callable) -> Callable:
    """
    Decorator to require task_id argument.
    
    Usage:
        @require_task
        async def execute(self, task_id: str, **kwargs):
            ...
    
    Args:
        func: Function to decorate
    
    Returns:
        Decorated function
    """
    @wraps(func)
    async def wrapper(self, **kwargs):
        if "task_id" not in kwargs or not kwargs["task_id"]:
            raise ValueError("task_id is required")
        return await func(self, **kwargs)
    return wrapper


def validate_enum(param_name: str, allowed_values: list[str]) -> Callable:
    """
    Decorator to validate enum parameter.
    
    Usage:
        @validate_enum("status", ["open", "closed", "in_progress"])
        async def execute(self, status: str, **kwargs):
            ...
    
    Args:
        param_name: Parameter name to validate
        allowed_values: List of allowed values
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, **kwargs):
            if param_name in kwargs:
                value = kwargs[param_name]
                if value not in allowed_values:
                    raise ValueError(
                        f"{param_name} must be one of {allowed_values}, "
                        f"got: {value}"
                    )
            return await func(self, **kwargs)
        return wrapper
    return decorator


def default_value(param_name: str, default: Any) -> Callable:
    """
    Decorator to provide default value for parameter.
    
    Usage:
        @default_value("limit", 100)
        async def execute(self, limit: int = 100, **kwargs):
            ...
    
    Args:
        param_name: Parameter name
        default: Default value
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, **kwargs):
            if param_name not in kwargs:
                kwargs[param_name] = default
            return await func(self, **kwargs)
        return wrapper
    return decorator


def log_execution(func: Callable) -> Callable:
    """
    Decorator to log tool execution.
    
    Usage:
        @log_execution
        async def execute(self, **kwargs):
            ...
    
    Args:
        func: Function to decorate
    
    Returns:
        Decorated function
    """
    @wraps(func)
    async def wrapper(self, **kwargs):
        tool_name = self.__class__.__name__
        logger.info(f"[{tool_name}] Starting execution")
        
        try:
            result = await func(self, **kwargs)
            logger.info(f"[{tool_name}] Execution completed successfully")
            return result
        except Exception as e:
            logger.error(f"[{tool_name}] Execution failed: {e}")
            raise
    
    return wrapper


