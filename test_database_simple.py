#!/usr/bin/env python3
"""
Simple database test
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

async def test_database_simple():
    """Test database models"""
    print("🧪 Testing Database Models")
    print("=" * 30)
    
    try:
        # Test 1: Import models
        print("1. Testing model imports...")
        from database.models import Project, Task, User, ProjectCreate, TaskCreate, UserCreate
        print("✅ Models imported successfully")
        
        # Test 2: Create Project
        print("2. Testing Project creation...")
        project = Project(
            id=str(uuid.uuid4()),
            name="Test Project",
            description="A test project",
            status="planning",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        print(f"✅ Project created: {project.name}")
        
        # Test 3: Create ProjectCreate
        print("3. Testing ProjectCreate...")
        project_create = ProjectCreate(
            name="New Project",
            description="A new project",
            domain="software",
            priority="high",
            timeline_weeks=12,
            budget=50000.0
        )
        print(f"✅ ProjectCreate created: {project_create.name}")
        
        # Test 4: Create Task
        print("4. Testing Task creation...")
        task = Task(
            id=str(uuid.uuid4()),
            project_id=project.id,
            title="Test Task",
            description="A test task",
            status="pending",
            priority="medium",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        print(f"✅ Task created: {task.title}")
        
        # Test 5: Create User
        print("5. Testing User creation...")
        user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            name="Test User",
            role="developer",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        print(f"✅ User created: {user.name}")
        
        # Test 6: JSON serialization
        print("6. Testing JSON serialization...")
        project_dict = project.dict()
        print(f"✅ Project dict: {len(project_dict)} fields")
        
        task_dict = task.dict()
        print(f"✅ Task dict: {len(task_dict)} fields")
        
        user_dict = user.dict()
        print(f"✅ User dict: {len(user_dict)} fields")
        
        print("\n🎉 Database test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database_simple())
    sys.exit(0 if success else 1)
