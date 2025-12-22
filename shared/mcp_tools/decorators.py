"""
Decorators for MCP tool registration and configuration.

These decorators provide a clean way to declare tool metadata
and add common behaviors to tools.
"""

from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar


# Storage for tool metadata
_tool_metadata: Dict[Type, Dict[str, Any]] = {}


def mcp_tool(
    name: str,
    description: str,
    input_schema: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
):
    """
    Decorator to register MCP tool metadata.
    
    Usage:
        @mcp_tool(
            name="list_tasks",
            description="List tasks from PM providers",
            input_schema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"}
                }
            }
        )
        class ListTasksTool(ReadTool):
            ...
    
    Args:
        name: Tool name for MCP registration
        description: Tool description for LLM
        input_schema: JSON Schema for input parameters
        tags: Optional list of tags for categorization
    """
    def decorator(cls: Type) -> Type:
        _tool_metadata[cls] = {
            "name": name,
            "description": description,
            "input_schema": input_schema or {"type": "object", "properties": {}},
            "tags": tags or [],
        }
        
        # Add properties to the class
        original_name = getattr(cls, "name", None)
        original_description = getattr(cls, "description", None)
        
        @property
        def tool_name(self) -> str:
            return name
        
        @property
        def tool_description(self) -> str:
            return description
        
        # Only set if not already defined by subclass
        if original_name is None or isinstance(original_name, property):
            if not hasattr(cls, '_name_set'):
                cls.name = tool_name
                cls._name_set = True
                
        if original_description is None or isinstance(original_description, property):
            if not hasattr(cls, '_description_set'):
                cls.description = tool_description  
                cls._description_set = True
        
        return cls
    
    return decorator


def get_tool_metadata(cls: Type) -> Optional[Dict[str, Any]]:
    """Get metadata for a tool class"""
    return _tool_metadata.get(cls)


def require_project(func: Callable) -> Callable:
    """
    Decorator that requires a project_id parameter.
    
    Will raise an error if project_id is not provided or empty.
    
    Usage:
        @require_project
        async def execute(self, project_id: str, **kwargs):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        project_id = kwargs.get('project_id')
        if not project_id:
            from shared.mcp_tools.base import ToolResult
            return ToolResult.fail("project_id is required")
        return await func(*args, **kwargs)
    
    return wrapper


def require_sprint(func: Callable) -> Callable:
    """
    Decorator that requires a sprint_id parameter.
    
    Will raise an error if sprint_id is not provided or empty.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        sprint_id = kwargs.get('sprint_id')
        if not sprint_id:
            from shared.mcp_tools.base import ToolResult
            return ToolResult.fail("sprint_id is required")
        return await func(*args, **kwargs)
    
    return wrapper


def default_value(param_name: str, value: Any):
    """
    Decorator to set a default value for a parameter.
    
    Usage:
        @default_value("limit", 50)
        async def execute(self, limit: int = None, **kwargs):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if kwargs.get(param_name) is None:
                kwargs[param_name] = value
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def cache_result(ttl_seconds: int = 300):
    """
    Decorator to cache tool results.
    
    Usage:
        @cache_result(ttl_seconds=600)
        async def execute(self, **kwargs):
            ...
    """
    def decorator(func: Callable) -> Callable:
        _cache: Dict[str, tuple] = {}  # key -> (result, timestamp)
        
        @wraps(func)
        async def wrapper(self, **kwargs):
            import time
            import json
            
            # Generate cache key
            cache_key = json.dumps(sorted(kwargs.items()), default=str)
            
            # Check cache
            if cache_key in _cache:
                result, cached_at = _cache[cache_key]
                if time.time() - cached_at < ttl_seconds:
                    return result
            
            # Execute and cache
            result = await func(self, **kwargs)
            _cache[cache_key] = (result, time.time())
            
            return result
        
        return wrapper
    return decorator


def validate_schema(schema: Dict[str, Any]):
    """
    Decorator to validate input against a JSON schema.
    
    Usage:
        @validate_schema({
            "type": "object",
            "required": ["project_id"],
            "properties": {...}
        })
        async def execute(self, **kwargs):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, **kwargs):
            try:
                import jsonschema
                jsonschema.validate(kwargs, schema)
            except ImportError:
                # jsonschema not installed, skip validation
                pass
            except Exception as e:
                from shared.mcp_tools.base import ToolResult
                return ToolResult.fail(f"Validation error: {str(e)}")
            
            return await func(self, **kwargs)
        
        return wrapper
    return decorator
