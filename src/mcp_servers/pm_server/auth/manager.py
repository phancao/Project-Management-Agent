"""
Authentication Manager

Manages user authentication, token generation, and authorization.
"""

import hashlib
import logging
import secrets
from datetime import datetime
from typing import Optional

from .models import User, Token, Role, Permission, TOOL_PERMISSIONS

logger = logging.getLogger(__name__)


class AuthManager:
    """
    Manages authentication and authorization for PM MCP Server.
    
    Features:
    - Token-based authentication
    - Role-based access control (RBAC)
    - Permission management
    - Token lifecycle management
    - Audit logging
    """
    
    def __init__(self):
        """Initialize auth manager."""
        self.users: dict[str, User] = {}
        self.tokens: dict[str, Token] = {}
        self.token_to_user: dict[str, str] = {}
        
        # Create default admin user
        self._create_default_users()
    
    def _create_default_users(self) -> None:
        """Create default users for testing."""
        # Admin user
        admin = User(
            id="admin-001",
            username="admin",
            email="admin@pm-mcp.local",
            role=Role.ADMIN,
        )
        self.users[admin.id] = admin
        
        # Developer user
        dev = User(
            id="dev-001",
            username="developer",
            email="dev@pm-mcp.local",
            role=Role.DEVELOPER,
        )
        self.users[dev.id] = dev
        
        # Viewer user
        viewer = User(
            id="viewer-001",
            username="viewer",
            email="viewer@pm-mcp.local",
            role=Role.VIEWER,
        )
        self.users[viewer.id] = viewer
        
        # Agent user
        agent = User(
            id="agent-001",
            username="deerflow-agent",
            email="agent@pm-mcp.local",
            role=Role.AGENT,
        )
        self.users[agent.id] = agent
        
        logger.info(f"Created {len(self.users)} default users")
    
    def generate_token(
        self,
        user_id: str,
        expires_in_hours: int = 24
    ) -> Optional[str]:
        """
        Generate authentication token for a user.
        
        Args:
            user_id: User ID
            expires_in_hours: Token expiration time in hours
            
        Returns:
            Token string or None if user not found
        """
        if user_id not in self.users:
            logger.warning(f"Cannot generate token: user {user_id} not found")
            return None
        
        # Generate secure random token
        token_str = secrets.token_urlsafe(32)
        
        # Create token object
        token = Token.create(
            token=token_str,
            user_id=user_id,
            expires_in_hours=expires_in_hours
        )
        
        # Store token
        self.tokens[token_str] = token
        self.token_to_user[token_str] = user_id
        
        # Update user last login
        self.users[user_id].last_login = datetime.utcnow()
        
        logger.info(
            f"Generated token for user {user_id} "
            f"(expires in {expires_in_hours}h)"
        )
        
        return token_str
    
    def validate_token(self, token: str) -> Optional[User]:
        """
        Validate token and return associated user.
        
        Args:
            token: Token string
            
        Returns:
            User object if token is valid, None otherwise
        """
        if token not in self.tokens:
            logger.debug(f"Token not found: {token[:10]}...")
            return None
        
        token_obj = self.tokens[token]
        
        if not token_obj.is_valid():
            logger.debug(f"Token expired or revoked: {token[:10]}...")
            return None
        
        user_id = self.token_to_user.get(token)
        if not user_id or user_id not in self.users:
            logger.warning(f"User not found for token: {token[:10]}...")
            return None
        
        user = self.users[user_id]
        
        if not user.is_active:
            logger.warning(f"User {user_id} is inactive")
            return None
        
        return user
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke a token.
        
        Args:
            token: Token string
            
        Returns:
            True if token was revoked, False otherwise
        """
        if token not in self.tokens:
            return False
        
        self.tokens[token].revoke()
        logger.info(f"Revoked token: {token[:10]}...")
        return True
    
    def check_permission(
        self,
        user: User,
        permission: Permission
    ) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user: User object
            permission: Permission to check
            
        Returns:
            True if user has permission, False otherwise
        """
        has_perm = user.has_permission(permission)
        
        if not has_perm:
            logger.debug(
                f"Permission denied: user {user.username} "
                f"does not have {permission.value}"
            )
        
        return has_perm
    
    def check_tool_access(
        self,
        user: User,
        tool_name: str
    ) -> bool:
        """
        Check if user has access to a specific tool.
        
        Args:
            user: User object
            tool_name: Name of the tool
            
        Returns:
            True if user has access, False otherwise
        """
        # Admin has access to all tools
        if user.has_permission(Permission.ADMIN_ALL):
            return True
        
        # Get required permissions for tool
        required_permissions = TOOL_PERMISSIONS.get(tool_name, [])
        
        if not required_permissions:
            # Tool not in mapping, allow by default (can be changed)
            logger.warning(
                f"Tool {tool_name} not in permission mapping, "
                f"allowing access for {user.username}"
            )
            return True
        
        # Check if user has any of the required permissions
        has_access = user.has_any_permission(required_permissions)
        
        if not has_access:
            logger.info(
                f"Access denied: user {user.username} "
                f"cannot access tool {tool_name}"
            )
        
        return has_access
    
    def create_user(
        self,
        username: str,
        email: str,
        role: Role,
        permissions: Optional[list[Permission]] = None
    ) -> User:
        """
        Create a new user.
        
        Args:
            username: Username
            email: Email address
            role: User role
            permissions: Custom permissions (optional)
            
        Returns:
            Created user object
        """
        user_id = f"user-{hashlib.md5(username.encode()).hexdigest()[:8]}"
        
        user = User(
            id=user_id,
            username=username,
            email=email,
            role=role,
            permissions=permissions or []
        )
        
        self.users[user_id] = user
        logger.info(f"Created user: {username} ({role.value})")
        
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def list_users(self) -> list[User]:
        """List all users."""
        return list(self.users.values())
    
    def update_user_role(self, user_id: str, role: Role) -> bool:
        """Update user role."""
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        old_role = user.role
        user.role = role
        
        # Reset permissions based on new role
        from .models import ROLE_PERMISSIONS
        user.permissions = ROLE_PERMISSIONS.get(role, [])
        
        logger.info(
            f"Updated user {user.username} role: "
            f"{old_role.value} -> {role.value}"
        )
        
        return True
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user."""
        if user_id not in self.users:
            return False
        
        self.users[user_id].is_active = False
        logger.info(f"Deactivated user: {user_id}")
        
        return True
    
    def activate_user(self, user_id: str) -> bool:
        """Activate a user."""
        if user_id not in self.users:
            return False
        
        self.users[user_id].is_active = True
        logger.info(f"Activated user: {user_id}")
        
        return True
    
    def get_stats(self) -> dict:
        """Get authentication statistics."""
        active_tokens = sum(
            1 for token in self.tokens.values()
            if token.is_valid()
        )
        
        return {
            "total_users": len(self.users),
            "active_users": sum(1 for u in self.users.values() if u.is_active),
            "total_tokens": len(self.tokens),
            "active_tokens": active_tokens,
            "users_by_role": {
                role.value: sum(
                    1 for u in self.users.values()
                    if u.role == role
                )
                for role in Role
            }
        }

