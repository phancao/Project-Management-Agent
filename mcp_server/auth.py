"""
MCP Server Authentication - DEPRECATED

This module is deprecated. Use AuthManager directly:

    from mcp_server.core import AuthManager
    
    auth_manager = AuthManager(db_session)
    user_id = await auth_manager.validate_api_key("mcp_xxx")

These functions are kept for backward compatibility only.
"""

from mcp_server.core.auth_manager import AuthManager

# Re-export for backward compatibility
validate_mcp_api_key = AuthManager.validate_api_key_static
generate_mcp_api_key = AuthManager.generate_api_key
create_user_api_key = AuthManager.create_api_key_static
revoke_user_api_key = AuthManager.revoke_api_key_static
