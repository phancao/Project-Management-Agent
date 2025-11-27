"""
Authentication Manager for MCP Server

Provides a clean interface for authentication operations.
Encapsulates all API key validation and management logic.
"""

import logging
import secrets
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AuthManager:
    """
    Manager for MCP Server authentication.
    
    Handles:
    - API key validation
    - API key generation
    - API key lifecycle management (create, revoke, expire)
    
    Usage:
        auth_manager = AuthManager(db_session)
        user_id = await auth_manager.validate_api_key("mcp_xxx")
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize AuthManager.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    async def validate_api_key(self, api_key: str) -> Optional[str]:
        """
        Validate an MCP API key and return the associated user_id.
        
        Args:
            api_key: API key to validate (format: "mcp_xxx" or "Bearer mcp_xxx")
            
        Returns:
            user_id (UUID string) if valid, None otherwise
        """
        if not api_key:
            return None
        
        # Remove "Bearer " prefix if present
        if api_key.startswith("Bearer "):
            api_key = api_key[7:]
        
        original_key = api_key
        
        try:
            from ..database.models import UserMCPAPIKey
            
            # Try to find key with original format
            key_record = self._find_api_key(original_key)
            
            # If not found and key has mcp_ prefix, try without prefix
            if not key_record and original_key.startswith("mcp_"):
                key_record = self._find_api_key(original_key[4:])
            
            # If not found and key doesn't have mcp_ prefix, try with prefix
            if not key_record and not original_key.startswith("mcp_"):
                key_record = self._find_api_key(f"mcp_{original_key}")
            
            if not key_record:
                logger.warning(f"[AuthManager] Invalid API key: {api_key[:10]}...")
                return None
            
            # Check expiration
            if key_record.expires_at and key_record.expires_at < datetime.utcnow():
                logger.warning(f"[AuthManager] Expired API key: {api_key[:10]}...")
                return None
            
            # Update last_used_at
            key_record.last_used_at = datetime.utcnow()
            self.db.commit()
            
            logger.debug(f"[AuthManager] Valid API key for user: {key_record.user_id}")
            return str(key_record.user_id)
            
        except Exception as e:
            logger.error(f"[AuthManager] Error validating API key: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    def _find_api_key(self, api_key: str):
        """Find an active API key record."""
        from ..database.models import UserMCPAPIKey
        
        return self.db.query(UserMCPAPIKey).filter(
            UserMCPAPIKey.api_key == api_key,
            UserMCPAPIKey.is_active == True  # noqa: E712
        ).first()
    
    async def create_api_key(
        self,
        user_id: str,
        name: Optional[str] = None,
        expires_in_days: Optional[int] = None
    ) -> Optional[str]:
        """
        Create a new MCP API key for a user.
        
        Args:
            user_id: User UUID
            name: Optional name for the key (e.g., "Cursor Desktop")
            expires_in_days: Optional expiration in days
            
        Returns:
            API key string if successful, None otherwise
        """
        try:
            from ..database.models import UserMCPAPIKey
            from datetime import timedelta
            
            api_key = self.generate_api_key()
            
            expires_at = None
            if expires_in_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            
            key_record = UserMCPAPIKey(
                user_id=user_id,
                api_key=api_key,
                name=name,
                is_active=True,
                expires_at=expires_at
            )
            
            self.db.add(key_record)
            self.db.commit()
            
            logger.info(f"[AuthManager] Created API key for user: {user_id}, name: {name}")
            return api_key
            
        except Exception as e:
            logger.error(f"[AuthManager] Error creating API key: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    async def revoke_api_key(self, api_key: str, user_id: Optional[str] = None) -> bool:
        """
        Revoke (deactivate) an API key.
        
        Args:
            api_key: API key to revoke
            user_id: Optional user ID for verification
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from ..database.models import UserMCPAPIKey
            
            query = self.db.query(UserMCPAPIKey).filter(
                UserMCPAPIKey.api_key == api_key
            )
            
            if user_id:
                query = query.filter(UserMCPAPIKey.user_id == user_id)
            
            key_record = query.first()
            
            if not key_record:
                return False
            
            key_record.is_active = False  # type: ignore
            self.db.commit()
            
            logger.info(f"[AuthManager] Revoked API key: {api_key[:10]}...")
            return True
            
        except Exception as e:
            logger.error(f"[AuthManager] Error revoking API key: {e}", exc_info=True)
            self.db.rollback()
            return False
    
    async def list_user_api_keys(self, user_id: str) -> list:
        """
        List all API keys for a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of API key info (without the actual key for security)
        """
        try:
            from ..database.models import UserMCPAPIKey
            
            keys = self.db.query(UserMCPAPIKey).filter(
                UserMCPAPIKey.user_id == user_id
            ).all()
            
            return [
                {
                    "id": str(k.id),
                    "name": k.name,
                    "is_active": k.is_active,
                    "created_at": k.created_at.isoformat() if k.created_at else None,
                    "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                    "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                    # Show only first 10 chars of key for identification
                    "key_preview": str(k.api_key)[:10] + "..." if k.api_key else None,
                }
                for k in keys
            ]
            
        except Exception as e:
            logger.error(f"[AuthManager] Error listing API keys: {e}", exc_info=True)
            return []
    
    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a new MCP API key.
        
        Returns:
            API key in format "mcp_<64-hex-chars>"
        """
        random_bytes = secrets.token_bytes(32)
        hex_key = random_bytes.hex()
        return f"mcp_{hex_key}"
    
    @classmethod
    def from_db_session(cls, db_session: Session) -> "AuthManager":
        """Create AuthManager from database session."""
        return cls(db_session)
    
    # =========================================================================
    # Static convenience methods (for backward compatibility with auth.py)
    # These create a new AuthManager instance for each call.
    # For better performance, create AuthManager once and reuse it.
    # =========================================================================
    
    @staticmethod
    async def validate_api_key_static(api_key: str) -> Optional[str]:
        """Static method for backward compatibility."""
        from ..database.connection import get_mcp_db_session
        db = next(get_mcp_db_session())
        try:
            return await AuthManager(db).validate_api_key(api_key)
        finally:
            db.close()
    
    @staticmethod
    async def create_api_key_static(user_id: str, name: Optional[str] = None) -> Optional[str]:
        """Static method for backward compatibility."""
        from ..database.connection import get_mcp_db_session
        db = next(get_mcp_db_session())
        try:
            return await AuthManager(db).create_api_key(user_id, name)
        finally:
            db.close()
    
    @staticmethod
    async def revoke_api_key_static(api_key: str, user_id: Optional[str] = None) -> bool:
        """Static method for backward compatibility."""
        from ..database.connection import get_mcp_db_session
        db = next(get_mcp_db_session())
        try:
            return await AuthManager(db).revoke_api_key(api_key, user_id)
        finally:
            db.close()
    
    # =========================================================================
    # HTTP Request Authentication (for FastAPI endpoints)
    # =========================================================================
    
    @staticmethod
    async def extract_user_from_request(request, require_auth: bool = True) -> Optional[str]:
        """
        Extract user ID from HTTP request.
        
        Checks (in order):
        1. X-MCP-API-Key header
        2. Authorization header (Bearer token)
        3. api_key query parameter
        4. X-User-ID header (for internal/testing)
        5. user_id query parameter
        
        Args:
            request: FastAPI Request object
            require_auth: If True, raises HTTPException 401 if no auth found
            
        Returns:
            user_id (UUID string) if authenticated, None otherwise
            
        Raises:
            HTTPException: 401 if require_auth=True and no valid auth found
        """
        from fastapi import HTTPException
        from ..database.connection import get_mcp_db_session
        
        user_id = None
        
        # Method 1: MCP API Key
        api_key = (
            request.headers.get("X-MCP-API-Key") or
            request.headers.get("Authorization") or
            request.query_params.get("api_key")
        )
        
        if api_key:
            # Remove "Bearer " prefix if present
            if api_key.startswith("Bearer "):
                api_key = api_key[7:]
            
            db = next(get_mcp_db_session())
            try:
                user_id = await AuthManager(db).validate_api_key(api_key)
            finally:
                db.close()
        
        # Method 2: Direct user ID (for internal/testing)
        if not user_id:
            user_id = (
                request.headers.get("X-User-ID") or 
                request.query_params.get("user_id")
            )
        
        # Enforce authentication if required
        if require_auth and not user_id:
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Provide X-MCP-API-Key header."
            )
        
        return user_id

