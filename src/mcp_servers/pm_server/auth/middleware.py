"""
Authentication Middleware

FastAPI middleware for token-based authentication.
"""

import logging
from typing import Callable, Optional

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from .manager import AuthManager
from .models import User

logger = logging.getLogger(__name__)

# HTTP Bearer token security
security = HTTPBearer(auto_error=False)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for authenticating requests.
    
    Extracts Bearer token from Authorization header and validates it.
    Attaches user object to request state if authenticated.
    """
    
    def __init__(self, app, auth_manager: AuthManager):
        """
        Initialize auth middleware.
        
        Args:
            app: FastAPI application
            auth_manager: Authentication manager instance
        """
        super().__init__(app)
        self.auth_manager = auth_manager
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request and validate authentication."""
        
        # Skip auth for public endpoints
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)
        
        # Extract token from Authorization header
        token = self._extract_token(request)
        
        if token:
            # Validate token and get user
            user = self.auth_manager.validate_token(token)
            
            if user:
                # Attach user to request state
                request.state.user = user
                request.state.authenticated = True
                logger.debug(f"Authenticated user: {user.username}")
            else:
                request.state.user = None
                request.state.authenticated = False
                logger.debug("Invalid or expired token")
        else:
            request.state.user = None
            request.state.authenticated = False
        
        # Continue processing request
        response = await call_next(request)
        return response
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (no auth required)."""
        public_endpoints = [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/token",
        ]
        
        return any(path.startswith(endpoint) for endpoint in public_endpoints)
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract Bearer token from Authorization header."""
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return None
        
        # Expected format: "Bearer <token>"
        parts = auth_header.split()
        
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.debug("Invalid Authorization header format")
            return None
        
        return parts[1]


def get_current_user(request: Request) -> User:
    """
    Dependency to get current authenticated user.
    
    Args:
        request: FastAPI request
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if not hasattr(request.state, "authenticated") or not request.state.authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return request.state.user


def get_optional_user(request: Request) -> Optional[User]:
    """
    Dependency to get current user if authenticated, None otherwise.
    
    Args:
        request: FastAPI request
        
    Returns:
        Current user or None
    """
    if hasattr(request.state, "user"):
        return request.state.user
    return None

