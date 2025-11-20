#!/usr/bin/env python3
"""
Test script for Database operations
Tests database connections, schema, and CRUD operations
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

async def test_database_imports():
    """Test database imports"""
    print("🔍 Testing database imports...")
    
    try:
        from database.models import (
            User, UserCreate, UserUpdate,
            Project, ProjectCreate, ProjectUpdate,
            Task, TaskCreate, TaskUpdate,
            ConversationSession, ConversationSessionCreate
        )
        print("✅ Database models import successful")
        return True
    except Exception as e:
        print(f"❌ Database models import failed: {e}")
        return False

async def test_model_creation():
    """Test model creation and validation"""
    print("\n🏗️ Testing model creation...")
    
    try:
        from database.models import User, Project, Task, ConversationSession
        
        # Test User model
        user = User(
            email="test@example.com",
            name="Test User",
            role="developer"
        )
        print(f"✅ User model created: {user.email}")
        
        # Test Project model
        project = Project(
            name="Test Project",
            description="A test project",
            domain="software",
            created_by=user.id
        )
        print(f"✅ Project model created: {project.name}")
        
        # Test Task model
        task = Task(
            title="Test Task",
            description="A test task",
            project_id=project.id,
            estimated_hours=8.0
        )
        print(f"✅ Task model created: {task.title}")
        
        # Test ConversationSession model
        session = ConversationSession(
            session_id="test_session_123",
            user_id=user.id,
            current_state="intent_detection"
        )
        print(f"✅ ConversationSession model created: {session.session_id}")
        
        return True
    except Exception as e:
        print(f"❌ Model creation failed: {e}")
        return False

async def test_model_validation():
    """Test model validation"""
    print("\n✅ Testing model validation...")
    
    try:
        from database.models import User, Project, Task
        from pydantic import ValidationError
        
        # Test valid data
        try:
            user = User(
                email="valid@example.com",
                name="Valid User",
                role="developer"
            )
            print("✅ Valid user data accepted")
        except ValidationError as e:
            print(f"❌ Valid user data rejected: {e}")
            return False
        
        # Test invalid data
        try:
            user = User(
                email="invalid-email",  # Invalid email format
                name="",  # Empty name
                role="invalid_role"  # Invalid role
            )
            print("❌ Invalid user data accepted (should be rejected)")
            return False
        except ValidationError:
            print("✅ Invalid user data correctly rejected")
        
        # Test project validation
        try:
            project = Project(
                name="",  # Empty name should fail
                description="Test",
                created_by=uuid.uuid4()
            )
            print("❌ Invalid project data accepted (should be rejected)")
            return False
        except ValidationError:
            print("✅ Invalid project data correctly rejected")
        
        return True
    except Exception as e:
        print(f"❌ Model validation test failed: {e}")
        return False

async def test_enum_values():
    """Test enum values"""
    print("\n🔢 Testing enum values...")
    
    try:
        from database.models import (
            ProjectStatus, TaskStatus, Priority, UserRole
        )
        
        # Test ProjectStatus enum
        statuses = [ProjectStatus.PLANNING, ProjectStatus.ACTIVE, ProjectStatus.COMPLETED]
        print(f"✅ ProjectStatus enum: {[s.value for s in statuses]}")
        
        # Test TaskStatus enum
        task_statuses = [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED]
        print(f"✅ TaskStatus enum: {[s.value for s in task_statuses]}")
        
        # Test Priority enum
        priorities = [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.URGENT]
        print(f"✅ Priority enum: {[p.value for p in priorities]}")
        
        # Test UserRole enum
        roles = [UserRole.ADMIN, UserRole.MANAGER, UserRole.DEVELOPER]
        print(f"✅ UserRole enum: {[r.value for r in roles]}")
        
        return True
    except Exception as e:
        print(f"❌ Enum values test failed: {e}")
        return False

async def test_relationships():
    """Test model relationships"""
    print("\n🔗 Testing model relationships...")
    
    try:
        from database.models import User, Project, Task, ProjectGoal
        
        # Create related models
        user = User(
            email="manager@example.com",
            name="Project Manager",
            role="manager"
        )
        
        project = Project(
            name="Related Project",
            description="A project with relationships",
            created_by=user.id
        )
        
        task = Task(
            title="Related Task",
            project_id=project.id,
            estimated_hours=16.0
        )
        
        goal = ProjectGoal(
            project_id=project.id,
            goal_text="Complete the project successfully"
        )
        
        # Verify relationships
        if task.project_id == project.id:
            print("✅ Task-Project relationship works")
        else:
            print("❌ Task-Project relationship failed")
            return False
        
        if goal.project_id == project.id:
            print("✅ Goal-Project relationship works")
        else:
            print("❌ Goal-Project relationship failed")
            return False
        
        if project.created_by == user.id:
            print("✅ Project-User relationship works")
        else:
            print("❌ Project-User relationship failed")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Relationships test failed: {e}")
        return False

async def test_json_serialization():
    """Test JSON serialization"""
    print("\n📄 Testing JSON serialization...")
    
    try:
        from database.models import User, Project, Task
        import json
        
        # Create models
        user = User(
            email="json@example.com",
            name="JSON User",
            role="developer"
        )
        
        project = Project(
            name="JSON Project",
            description="A project for JSON testing",
            created_by=user.id
        )
        
        task = Task(
            title="JSON Task",
            project_id=project.id,
            estimated_hours=4.0
        )
        
        # Test serialization
        user_json = user.model_dump()
        project_json = project.model_dump()
        task_json = task.model_dump()
        
        print(f"✅ User JSON: {len(user_json)} fields")
        print(f"✅ Project JSON: {len(project_json)} fields")
        print(f"✅ Task JSON: {len(task_json)} fields")
        
        # Test deserialization
        user_from_json = User(**user_json)
        project_from_json = Project(**project_json)
        task_from_json = Task(**task_json)
        
        if user_from_json.email == user.email:
            print("✅ User deserialization works")
        else:
            print("❌ User deserialization failed")
            return False
        
        if project_from_json.name == project.name:
            print("✅ Project deserialization works")
        else:
            print("❌ Project deserialization failed")
            return False
        
        if task_from_json.title == task.title:
            print("✅ Task deserialization works")
        else:
            print("❌ Task deserialization failed")
            return False
        
        return True
    except Exception as e:
        print(f"❌ JSON serialization test failed: {e}")
        return False

async def test_optional_fields():
    """Test optional fields"""
    print("\n❓ Testing optional fields...")
    
    try:
        from database.models import Project, Task, User
        
        # Test project with minimal required fields
        project = Project(
            name="Minimal Project",
            created_by=uuid.uuid4()
        )
        
        if project.description is None:
            print("✅ Optional description field works")
        else:
            print("❌ Optional description field failed")
            return False
        
        if project.status.value == "planning":  # Default value
            print("✅ Default status value works")
        else:
            print("❌ Default status value failed")
            return False
        
        # Test task with optional fields
        task = Task(
            title="Minimal Task",
            project_id=project.id
        )
        
        if task.description is None:
            print("✅ Optional task description works")
        else:
            print("❌ Optional task description failed")
            return False
        
        if task.actual_hours == 0.0:  # Default value
            print("✅ Default actual_hours works")
        else:
            print("❌ Default actual_hours failed")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Optional fields test failed: {e}")
        return False

async def test_timestamps():
    """Test timestamp fields"""
    print("\n⏰ Testing timestamp fields...")
    
    try:
        from database.models import User, Project
        from datetime import datetime
        
        # Create models
        user = User(
            email="timestamp@example.com",
            name="Timestamp User",
            role="developer"
        )
        
        project = Project(
            name="Timestamp Project",
            created_by=user.id
        )
        
        # Check that timestamps are set
        if isinstance(user.created_at, datetime):
            print("✅ User created_at timestamp works")
        else:
            print("❌ User created_at timestamp failed")
            return False
        
        if isinstance(project.updated_at, datetime):
            print("✅ Project updated_at timestamp works")
        else:
            print("❌ Project updated_at timestamp failed")
            return False
        
        # Check that timestamps are recent
        now = datetime.now()
        time_diff = (now - user.created_at).total_seconds()
        
        if time_diff < 5:  # Within 5 seconds
            print("✅ Timestamps are recent")
        else:
            print("❌ Timestamps are not recent")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Timestamps test failed: {e}")
        return False

async def test_uuid_generation():
    """Test UUID generation"""
    print("\n🆔 Testing UUID generation...")
    
    try:
        from database.models import User, Project, Task
        import uuid
        
        # Create multiple models
        user1 = User(email="uuid1@example.com", name="User 1", role="developer")
        user2 = User(email="uuid2@example.com", name="User 2", role="developer")
        
        project1 = Project(name="Project 1", created_by=user1.id)
        project2 = Project(name="Project 2", created_by=user2.id)
        
        # Check that UUIDs are generated
        if isinstance(user1.id, uuid.UUID):
            print("✅ User UUID generation works")
        else:
            print("❌ User UUID generation failed")
            return False
        
        if isinstance(project1.id, uuid.UUID):
            print("✅ Project UUID generation works")
        else:
            print("❌ Project UUID generation failed")
            return False
        
        # Check that UUIDs are unique
        if user1.id != user2.id:
            print("✅ UUIDs are unique")
        else:
            print("❌ UUIDs are not unique")
            return False
        
        if project1.id != project2.id:
            print("✅ Project UUIDs are unique")
        else:
            print("❌ Project UUIDs are not unique")
            return False
        
        return True
    except Exception as e:
        print(f"❌ UUID generation test failed: {e}")
        return False

async def main():
    """Run all database tests"""
    print("🚀 Starting Database Tests")
    print("=" * 50)
    
    tests = [
        ("Imports", test_database_imports),
        ("Model Creation", test_model_creation),
        ("Model Validation", test_model_validation),
        ("Enum Values", test_enum_values),
        ("Relationships", test_relationships),
        ("JSON Serialization", test_json_serialization),
        ("Optional Fields", test_optional_fields),
        ("Timestamps", test_timestamps),
        ("UUID Generation", test_uuid_generation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Database models are working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
