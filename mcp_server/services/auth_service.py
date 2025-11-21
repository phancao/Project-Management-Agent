"""
Authentication Service

Unified authentication service for MCP Server.
Handles API key validation and user identification.
"""

import logging
from typing import Optional
from fastapi import HTTPException, Request

from ..database.connection import get_mcp_db_session
from ..auth import validate_mcp_api_key

logger = logging.getLogger(__name__)


class AuthService:
    """Service for handling authentication and user identification."""
    
    @staticmethod
    async def extract_user_id(request: Request, require_auth: bool = True) -> Optional[str]:
        """
        Extract user ID from request using multiple methods.
        
        Priority:
        1. X-MCP-API-Key header (validates token → gets user_id)
        2. X-User-ID header (direct user ID - for internal/testing)
        3. Query parameter ?user_id=<uuid>
        
        Args:
            request: FastAPI request object
            require_auth: If True, raises 401 if no valid authentication found
            
        Returns:
            user_id (UUID string) if found, None otherwise
            
        Raises:
            HTTPException: 401 if require_auth=True and no valid auth found
        """
        user_id = None
        
        # Method 1: MCP API Key (recommended for external clients)
        api_key = (
            request.headers.get("X-MCP-API-Key") or
            request.headers.get("Authorization") or
            request.query_params.get("api_key")
        )
        
        if api_key:
            try:
                # Remove "Bearer " prefix if present
                if api_key.startswith("Bearer "):
                    api_key = api_key[7:]
                
                user_id = await validate_mcp_api_key(api_key)
                if user_id:
                    logger.info(f"[Auth] User identified via API key: {user_id}")
            except Exception as e:
                logger.warning(f"[Auth] API key validation failed: {e}")
        
        # Method 2: Direct user ID (for internal/testing - only if API key validation failed)
        if not user_id:
            user_id = (
                request.headers.get("X-User-ID") or 
                request.query_params.get("user_id")
            )
            if user_id:
                logger.info(f"[Auth] User ID provided directly: {user_id}")
        
        # Enforce authentication if required
        if require_auth and not user_id:
            logger.warning("[Auth] Unauthenticated connection attempt rejected")
            raise HTTPException(
                status_code=401,
                detail=(
                    "Authentication required. "
                    "Please provide X-MCP-API-Key header with a valid API key, "
                    "or X-User-ID header for direct user authentication."
                )
            )
        
        return user_id
    
    @staticmethod
    def should_require_auth(config) -> bool:
        """
        Determine if authentication should be required based on configuration.
        
        Args:
            config: PMServerConfig instance
            
        Returns:
            True if authentication should be required
        """
        # For production, always require auth
        # For development, check config.enable_auth
        import os
        environment = os.getenv("ENVIRONMENT", "development")
        
        if environment == "production":
            return True
        
        return config.enable_auth if hasattr(config, 'enable_auth') else False

