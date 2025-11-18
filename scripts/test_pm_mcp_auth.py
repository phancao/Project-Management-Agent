#!/usr/bin/env python3
"""
Test PM MCP Server Authentication

Tests authentication and authorization features.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_auth_models():
    """Test authentication models."""
    print("=" * 60)
    print("Test 1: Authentication Models")
    print("=" * 60)
    
    try:
        from src.mcp_servers.pm_server.auth.models import (
            User, Token, Role, Permission, ROLE_PERMISSIONS
        )
        
        # Create user
        user = User(
            id="test-001",
            username="testuser",
            email="test@example.com",
            role=Role.DEVELOPER
        )
        
        print(f"✅ Created user: {user.username}")
        print(f"   Role: {user.role.value}")
        print(f"   Permissions: {len(user.permissions)}")
        
        # Test permission check
        assert user.has_permission(Permission.TASK_READ)
        assert user.has_permission(Permission.PROJECT_READ)
        assert not user.has_permission(Permission.PROJECT_DELETE)
        
        print(f"✅ Permission checks working")
        
        # Create token
        token = Token.create(
            token="test-token-123",
            user_id=user.id,
            expires_in_hours=24
        )
        
        assert token.is_valid()
        print(f"✅ Token created and valid")
        
        # Test role permissions
        assert Role.ADMIN in ROLE_PERMISSIONS
        assert Permission.ADMIN_ALL in ROLE_PERMISSIONS[Role.ADMIN]
        print(f"✅ Role permissions configured")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_auth_manager():
    """Test authentication manager."""
    print("\n" + "=" * 60)
    print("Test 2: Authentication Manager")
    print("=" * 60)
    
    try:
        from src.mcp_servers.pm_server.auth.manager import AuthManager
        from src.mcp_servers.pm_server.auth.models import Role, Permission
        
        # Create auth manager
        auth_manager = AuthManager()
        
        print(f"✅ Auth manager created")
        print(f"   Default users: {len(auth_manager.users)}")
        
        # Test token generation
        token = auth_manager.generate_token("admin-001", expires_in_hours=1)
        assert token is not None
        print(f"✅ Generated token: {token[:20]}...")
        
        # Test token validation
        user = auth_manager.validate_token(token)
        assert user is not None
        assert user.username == "admin"
        print(f"✅ Token validated: {user.username}")
        
        # Test permission check
        assert auth_manager.check_permission(user, Permission.ADMIN_ALL)
        print(f"✅ Permission check working")
        
        # Test tool access
        assert auth_manager.check_tool_access(user, "list_projects")
        assert auth_manager.check_tool_access(user, "create_project")
        print(f"✅ Tool access check working")
        
        # Test token revocation
        assert auth_manager.revoke_token(token)
        user_after_revoke = auth_manager.validate_token(token)
        assert user_after_revoke is None
        print(f"✅ Token revocation working")
        
        # Test user creation
        new_user = auth_manager.create_user(
            username="newuser",
            email="new@example.com",
            role=Role.DEVELOPER
        )
        assert new_user.username == "newuser"
        print(f"✅ User creation working")
        
        # Test stats
        stats = auth_manager.get_stats()
        assert stats["total_users"] == 5  # 4 default + 1 new
        print(f"✅ Stats: {stats['total_users']} users, {stats['total_tokens']} tokens")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_auth_integration():
    """Test authentication integration."""
    print("\n" + "=" * 60)
    print("Test 3: Authentication Integration")
    print("=" * 60)
    
    try:
        from src.mcp_servers.pm_server.auth import (
            AuthManager,
            User,
            Role,
            Permission
        )
        
        # Test imports
        print(f"✅ All auth modules imported successfully")
        
        # Test role hierarchy
        roles = [Role.ADMIN, Role.PM, Role.DEVELOPER, Role.QC, Role.VIEWER, Role.AGENT]
        print(f"✅ {len(roles)} roles defined")
        
        # Test permissions
        permissions = [
            Permission.PROJECT_READ,
            Permission.PROJECT_WRITE,
            Permission.TASK_READ,
            Permission.TASK_WRITE,
            Permission.ADMIN_ALL
        ]
        print(f"✅ Permissions system configured")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "PM MCP SERVER AUTH TESTS" + " " * 19 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = []
    
    # Run tests
    results.append(await test_auth_models())
    results.append(await test_auth_manager())
    results.append(await test_auth_integration())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed!")
        print("\n📝 Next steps:")
        print("   1. Start PM MCP Server with auth:")
        print("      uv run python scripts/run_pm_mcp_server.py --transport http --port 8080")
        print("\n   2. Generate token:")
        print("      curl -X POST http://localhost:8080/auth/token \\")
        print("        -H 'Content-Type: application/json' \\")
        print("        -d '{\"username\":\"admin\",\"expires_in_hours\":24}'")
        print("\n   3. Use token:")
        print("      export TOKEN='your-token-here'")
        print("      curl -H \"Authorization: Bearer $TOKEN\" http://localhost:8080/projects")
        print("\n   4. See full guide: docs/PM_MCP_SERVER_AUTH_GUIDE.md")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

