"""
Authentication and Authorization for PM MCP Server

This module provides token-based authentication and role-based access control (RBAC)
for securing PM MCP Server operations.
"""

from .models import User, Role, Permission, Token
from .manager import AuthManager
from .middleware import AuthMiddleware
from .decorators import require_auth, require_permission, require_role

# Import API key validation from the top-level auth.py module
# Use importlib to avoid circular import issues
import importlib.util
import sys
from pathlib import Path

_auth_module_path = Path(__file__).parent.parent / "auth.py"
if _auth_module_path.exists():
    try:
        # Ensure mcp_server package is in sys.modules for relative imports
        if 'mcp_server' not in sys.modules:
            import mcp_server
        
        # Load auth.py as a proper module within mcp_server package
        spec = importlib.util.spec_from_file_location("mcp_server.auth", _auth_module_path)
        if spec and spec.loader:
            _auth_module = importlib.util.module_from_spec(spec)
            # Set package and name for relative imports to work
            _auth_module.__package__ = 'mcp_server'
            _auth_module.__name__ = 'mcp_server.auth'
            # Execute the module
            spec.loader.exec_module(_auth_module)
            validate_mcp_api_key = getattr(_auth_module, 'validate_mcp_api_key', None)
            generate_mcp_api_key = getattr(_auth_module, 'generate_mcp_api_key', None)
            create_user_api_key = getattr(_auth_module, 'create_user_api_key', None)
            revoke_user_api_key = getattr(_auth_module, 'revoke_user_api_key', None)
        else:
            validate_mcp_api_key = None
            generate_mcp_api_key = None
            create_user_api_key = None
            revoke_user_api_key = None
    except Exception as e:
        # If import fails, set to None
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to import auth.py functions: {e}", exc_info=True)
        validate_mcp_api_key = None
        generate_mcp_api_key = None
        create_user_api_key = None
        revoke_user_api_key = None
else:
    validate_mcp_api_key = None
    generate_mcp_api_key = None
    create_user_api_key = None
    revoke_user_api_key = None

__all__ = [
    "User",
    "Role",
    "Permission",
    "Token",
    "AuthManager",
    "AuthMiddleware",
    "require_auth",
    "require_permission",
    "require_role",
    "validate_mcp_api_key",
    "generate_mcp_api_key",
    "create_user_api_key",
    "revoke_user_api_key",
]

