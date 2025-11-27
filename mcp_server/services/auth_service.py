"""
Authentication Service - DEPRECATED

This module is deprecated. Use AuthManager directly:

    from mcp_server.core import AuthManager
    
    auth_manager = AuthManager(db_session)
    user_id = await auth_manager.validate_api_key(api_key)

For HTTP request authentication, use AuthManager.extract_user_from_request().
"""

from typing import Optional
from mcp_server.core.auth_manager import AuthManager


class AuthService:
    """
    DEPRECATED: Use AuthManager directly.
    
    This class exists only for backward compatibility.
    """
    
    @staticmethod
    async def extract_user_id(request, require_auth: bool = True) -> Optional[str]:
        """DEPRECATED: Use AuthManager.extract_user_from_request()"""
        return await AuthManager.extract_user_from_request(request, require_auth)
    
    @staticmethod
    def should_require_auth(_config=None) -> bool:
        """Authentication is ALWAYS required."""
        return True
