"""
MCP Server Authentication

Handles authentication for external clients connecting to the MCP Server.
Supports API key-based authentication to identify users.
"""

import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from ..database.connection import get_mcp_db_session

logger = logging.getLogger(__name__)


async def validate_mcp_api_key(api_key: str) -> Optional[str]:
    """
    Validate MCP API key and return user_id.
    
    Args:
        api_key: API key to validate (format: "mcp_xxx" or just the key)
        
    Returns:
        user_id (UUID string) if valid, None otherwise
    """
    if not api_key:
        return None
    
    # Remove "Bearer " prefix if present
    if api_key.startswith("Bearer "):
        api_key = api_key[7:]
    
    # Remove "mcp_" prefix if present (for consistency)
    if api_key.startswith("mcp_"):
        api_key = api_key[4:]
    
    db: Session = next(get_mcp_db_session())
    try:
        # Import here to avoid circular dependencies
        from .database.models import UserMCPAPIKey
        
        key_record = db.query(UserMCPAPIKey).filter(
            UserMCPAPIKey.api_key == api_key,
            UserMCPAPIKey.is_active == True
        ).first()
        
        if not key_record:
            logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
            return None
        
        # Check expiration
        if key_record.expires_at and key_record.expires_at < datetime.utcnow():
            logger.warning(f"Expired API key attempted: {api_key[:10]}...")
            return None
        
        # Update last_used_at
        key_record.last_used_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Valid API key for user: {key_record.user_id}")
        return str(key_record.user_id)
        
    except Exception as e:
        logger.error(f"Error validating API key: {e}", exc_info=True)
        db.rollback()
        return None
    finally:
        db.close()


def generate_mcp_api_key() -> str:
    """
    Generate a new MCP API key for external clients (Cursor, VS Code, etc.).
    
    This is NOT the same as PM Provider API keys (JIRA/OpenProject credentials).
    
    - MCP API Key: Used by Cursor to authenticate to MCP Server
    - PM Provider Key: Used by MCP Server to authenticate to JIRA/OpenProject
    
    Returns:
        API key in format "mcp_<64-hex-chars>"
    """
    import secrets
    
    # Generate 32 random bytes (64 hex characters)
    random_bytes = secrets.token_bytes(32)
    hex_key = random_bytes.hex()
    
    # Format: mcp_<hex>
    return f"mcp_{hex_key}"


async def create_user_api_key(user_id: str, name: Optional[str] = None) -> Optional[str]:
    """
    Create a new MCP API key for a user.
    
    This creates an API key that external clients (Cursor, VS Code, etc.) use
    to authenticate to the MCP Server. This is NOT the same as PM Provider
    API keys (JIRA/OpenProject credentials stored in pm_provider_connections).
    
    Args:
        user_id: User UUID
        name: Optional name for the key (e.g., "Cursor Desktop", "VS Code")
        
    Returns:
        MCP API key (format: "mcp_xxx") if successful, None otherwise
    """
    db: Session = next(get_mcp_db_session())
    try:
        from .database.models import UserMCPAPIKey
        
        api_key = generate_mcp_api_key()
        
        key_record = UserMCPAPIKey(
            user_id=user_id,
            api_key=api_key,
            name=name,
            is_active=True
        )
        
        db.add(key_record)
        db.commit()
        
        logger.info(f"Created API key for user: {user_id}, name: {name}")
        return api_key
        
    except Exception as e:
        logger.error(f"Error creating API key: {e}", exc_info=True)
        db.rollback()
        return None
    finally:
        db.close()


async def revoke_user_api_key(api_key: str, user_id: str) -> bool:
    """
    Revoke (deactivate) an API key.
    
    Args:
        api_key: API key to revoke
        user_id: User ID (for verification)
        
    Returns:
        True if successful, False otherwise
    """
    db: Session = next(get_mcp_db_session())
    try:
        from .database.models import UserMCPAPIKey
        
        key_record = db.query(UserMCPAPIKey).filter(
            UserMCPAPIKey.api_key == api_key,
            UserMCPAPIKey.user_id == user_id
        ).first()
        
        if not key_record:
            return False
        
        key_record.is_active = False
        db.commit()
        
        logger.info(f"Revoked API key for user: {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error revoking API key: {e}", exc_info=True)
        db.rollback()
        return False
    finally:
        db.close()

