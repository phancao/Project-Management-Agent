"""
Authentication Routes

FastAPI routes for authentication operations.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, Field

from .manager import AuthManager
from .middleware import get_current_user, get_optional_user
from .models import User, Role, Permission

logger = logging.getLogger(__name__)


# Request/Response Models
class TokenRequest(BaseModel):
    """Request to generate a token."""
    username: str = Field(..., description="Username")
    expires_in_hours: int = Field(24, description="Token expiration in hours")


class TokenResponse(BaseModel):
    """Response containing authentication token."""
    token: str
    user_id: str
    username: str
    role: str
    expires_in_hours: int


class UserInfo(BaseModel):
    """User information response."""
    id: str
    username: str
    email: str
    role: str
    permissions: list[str]
    is_active: bool
    created_at: str
    last_login: Optional[str] = None


class CreateUserRequest(BaseModel):
    """Request to create a new user."""
    username: str
    email: str
    role: Role
    permissions: Optional[list[Permission]] = None


class AuthStats(BaseModel):
    """Authentication statistics."""
    total_users: int
    active_users: int
    total_tokens: int
    active_tokens: int
    users_by_role: dict[str, int]


def create_auth_router(auth_manager: AuthManager) -> APIRouter:
    """
    Create authentication router with all auth endpoints.
    
    Args:
        auth_manager: Authentication manager instance
        
    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/auth", tags=["authentication"])
    
    @router.post("/token", response_model=TokenResponse)
    async def generate_token(request: TokenRequest):
        """
        Generate authentication token for a user.
        
        This endpoint generates a Bearer token that can be used to authenticate
        subsequent requests.
        """
        # Get user by username
        user = auth_manager.get_user_by_username(request.username)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{request.username}' not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is inactive"
            )
        
        # Generate token
        token = auth_manager.generate_token(
            user.id,
            expires_in_hours=request.expires_in_hours
        )
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate token"
            )
        
        return TokenResponse(
            token=token,
            user_id=user.id,
            username=user.username,
            role=user.role.value,
            expires_in_hours=request.expires_in_hours
        )
    
    @router.post("/revoke")
    async def revoke_token(
        request: Request,
        current_user: User = Depends(get_current_user)
    ):
        """
        Revoke current authentication token.
        
        Requires authentication.
        """
        # Extract token from request
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "")
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No token provided"
            )
        
        success = auth_manager.revoke_token(token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found"
            )
        
        return {"message": "Token revoked successfully"}
    
    @router.get("/me", response_model=UserInfo)
    async def get_current_user_info(
        current_user: User = Depends(get_current_user)
    ):
        """
        Get current user information.
        
        Requires authentication.
        """
        return UserInfo(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            role=current_user.role.value,
            permissions=[p.value for p in current_user.permissions],
            is_active=current_user.is_active,
            created_at=current_user.created_at.isoformat(),
            last_login=current_user.last_login.isoformat() if current_user.last_login else None
        )
    
    @router.get("/users", response_model=list[UserInfo])
    async def list_users(
        current_user: User = Depends(get_current_user)
    ):
        """
        List all users.
        
        Requires authentication. Only admins can see all users.
        """
        # Check if user is admin
        if not current_user.has_permission(Permission.ADMIN_ALL):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required"
            )
        
        users = auth_manager.list_users()
        
        return [
            UserInfo(
                id=user.id,
                username=user.username,
                email=user.email,
                role=user.role.value,
                permissions=[p.value for p in user.permissions],
                is_active=user.is_active,
                created_at=user.created_at.isoformat(),
                last_login=user.last_login.isoformat() if user.last_login else None
            )
            for user in users
        ]
    
    @router.post("/users", response_model=UserInfo)
    async def create_user(
        request: CreateUserRequest,
        current_user: User = Depends(get_current_user)
    ):
        """
        Create a new user.
        
        Requires admin permission.
        """
        # Check if user is admin
        if not current_user.has_permission(Permission.ADMIN_ALL):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required"
            )
        
        # Check if username already exists
        existing_user = auth_manager.get_user_by_username(request.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User '{request.username}' already exists"
            )
        
        # Create user
        user = auth_manager.create_user(
            username=request.username,
            email=request.email,
            role=request.role,
            permissions=request.permissions
        )
        
        return UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value,
            permissions=[p.value for p in user.permissions],
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            last_login=None
        )
    
    @router.get("/stats", response_model=AuthStats)
    async def get_auth_stats(
        current_user: User = Depends(get_current_user)
    ):
        """
        Get authentication statistics.
        
        Requires admin permission.
        """
        # Check if user is admin
        if not current_user.has_permission(Permission.ADMIN_ALL):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required"
            )
        
        stats = auth_manager.get_stats()
        
        return AuthStats(**stats)
    
    @router.get("/check")
    async def check_auth(
        user: Optional[User] = Depends(get_optional_user)
    ):
        """
        Check authentication status.
        
        Public endpoint that returns auth status.
        """
        if user:
            return {
                "authenticated": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role.value
                }
            }
        else:
            return {
                "authenticated": False,
                "user": None
            }
    
    return router

