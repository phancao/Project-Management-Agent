"""
Authentication Decorators

Decorators for protecting endpoints with authentication and authorization.
"""

import logging
from functools import wraps
from typing import Callable

from fastapi import HTTPException, status

from .models import Permission, Role

logger = logging.getLogger(__name__)


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for an endpoint.
    
    Usage:
        @app.get("/protected")
        @require_auth
        async def protected_endpoint(request: Request):
            user = request.state.user
            return {"message": f"Hello {user.username}"}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Get request from args or kwargs
        request = kwargs.get("request") or (args[0] if args else None)
        
        if not request:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Request object not found"
            )
        
        # Check if user is authenticated
        if not hasattr(request.state, "authenticated") or not request.state.authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return await func(*args, **kwargs)
    
    return wrapper


def require_permission(*permissions: Permission):
    """
    Decorator to require specific permissions for an endpoint.
    
    Usage:
        @app.post("/projects")
        @require_permission(Permission.PROJECT_WRITE)
        async def create_project(request: Request):
            # Only users with PROJECT_WRITE permission can access
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from args or kwargs
            request = kwargs.get("request") or (args[0] if args else None)
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )
            
            # Check if user is authenticated
            if not hasattr(request.state, "authenticated") or not request.state.authenticated:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user = request.state.user
            
            # Check if user has required permissions
            if not user.has_any_permission(list(permissions)):
                logger.warning(
                    f"Permission denied: user {user.username} "
                    f"does not have required permissions: {[p.value for p in permissions]}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {[p.value for p in permissions]}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def require_role(*roles: Role):
    """
    Decorator to require specific roles for an endpoint.
    
    Usage:
        @app.delete("/users/{user_id}")
        @require_role(Role.ADMIN)
        async def delete_user(request: Request, user_id: str):
            # Only admins can access
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from args or kwargs
            request = kwargs.get("request") or (args[0] if args else None)
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )
            
            # Check if user is authenticated
            if not hasattr(request.state, "authenticated") or not request.state.authenticated:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user = request.state.user
            
            # Check if user has required role
            if user.role not in roles:
                logger.warning(
                    f"Role check failed: user {user.username} "
                    f"has role {user.role.value}, required: {[r.value for r in roles]}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient role. Required: {[r.value for r in roles]}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator

