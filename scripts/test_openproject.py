#!/usr/bin/env python3
"""
Test script for OpenProject provider connection

Usage:
    python scripts/test_openproject.py
"""
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pm_providers import build_pm_provider, PMProject, PMTask
from database import get_db_session


async def test_openproject():
    """Test OpenProject provider connection and basic operations"""
    print("🧪 Testing OpenProject Provider Connection...")
    print("=" * 60)
    
    # Get database session
    db = next(get_db_session())
    
    # Build provider
    print("\n1️⃣ Building provider...")
    try:
        provider = build_pm_provider(db_session=db)
        if not provider:
            print("❌ No provider configured. Set PM_PROVIDER=openproject in .env")
            return False
        print(f"✅ Provider built: {provider.__class__.__name__}")
    except Exception as e:
        print(f"❌ Failed to build provider: {e}")
        return False
    
    # Test health check
    print("\n2️⃣ Testing health check...")
    try:
        is_healthy = await provider.health_check()
        if is_healthy:
            print("✅ Health check passed")
        else:
            print("❌ Health check failed - check credentials and URL")
            import traceback
            traceback.print_exc()
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test list projects
    print("\n3️⃣ Testing list projects...")
    try:
        projects = await provider.list_projects()
        print(f"✅ Found {len(projects)} projects")
        if projects:
            print(f"   Example: {projects[0].name} (ID: {projects[0].id})")
    except Exception as e:
        print(f"❌ Failed to list projects: {e}")
        return False
    
    # Test create project
    print("\n4️⃣ Testing create project...")
    try:
        test_project = PMProject(
            name=f"Test Project - {os.urandom(4).hex()}",
            description="Created by test script"
        )
        created = await provider.create_project(test_project)
        print(f"✅ Created project: {created.name} (ID: {created.id})")
        
        # Cleanup - delete test project
        try:
            await provider.delete_project(created.id)
            print(f"   🧹 Cleaned up test project")
        except:
            print(f"   ⚠️  Could not delete test project (manual cleanup may be needed)")
    except Exception as e:
        print(f"❌ Failed to create project: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test list tasks
    print("\n5️⃣ Testing list tasks...")
    try:
        tasks = await provider.list_tasks()
        print(f"✅ Found {len(tasks)} tasks")
        if tasks:
            print(f"   Example: {tasks[0].title} (ID: {tasks[0].id})")
    except Exception as e:
        print(f"❌ Failed to list tasks: {e}")
        return False
    
    # Test list users
    print("\n6️⃣ Testing list users...")
    try:
        users = await provider.list_users()
        print(f"✅ Found {len(users)} users")
        if users:
            print(f"   Example: {users[0].name} (ID: {users[0].id})")
    except Exception as e:
        print(f"❌ Failed to list users: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! OpenProject integration is working.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_openproject())
    sys.exit(0 if success else 1)

