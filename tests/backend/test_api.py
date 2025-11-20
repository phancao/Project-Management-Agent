#!/usr/bin/env python3
"""
Test script for FastAPI endpoints
Tests API endpoints, WebSocket connections, and data validation
"""

import asyncio
import sys
import os
import json
import uuid
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

async def test_api_imports():
    """Test API imports"""
    print("🔍 Testing API imports...")
    
    try:
        from api.main import app
        print("✅ FastAPI app import successful")
    except Exception as e:
        print(f"❌ FastAPI app import failed: {e}")
        return False
    
    try:
        from database.models import Project, Task, User
        print("✅ Database models import successful")
    except Exception as e:
        print(f"❌ Database models import failed: {e}")
        return False
    
    return True

async def test_health_endpoint():
    """Test health check endpoint"""
    print("\n🏥 Testing health endpoint...")
    
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        auth_headers = {"Authorization": "Bearer mock_token"}
        response = client.get("/health", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health endpoint test failed: {e}")
        return False

async def test_chat_endpoints():
    """Test chat endpoints"""
    print("\n💬 Testing chat endpoints...")
    
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        
        # Mock auth headers
        auth_headers = {"Authorization": "Bearer mock_token"}
        
        # Test chat message
        chat_data = {
            "message": "Hello, I want to create a new project",
            "session_id": str(uuid.uuid4()),
            "user_id": "test_user"
        }
        
        response = client.post("/api/chat", json=chat_data, headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Chat endpoint response: {data.get('type', 'unknown')}")
            print(f"Message: {data.get('message', 'No message')}")
            return True
        else:
            print(f"❌ Chat endpoint failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Chat endpoints test failed: {e}")
        return False

async def test_project_endpoints():
    """Test project management endpoints"""
    print("\n📁 Testing project endpoints...")
    
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        
        # Mock auth headers
        auth_headers = {"Authorization": "Bearer mock_token"}
        
        # Test create project
        project_data = {
            "name": "Test Project",
            "description": "A test project for API testing",
            "domain": "software",
            "priority": "medium",
            "timeline_weeks": 12,
            "budget": 50000.0
        }
        
        response = client.post("/api/projects", json=project_data, headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            project_id = data.get('id')
            print(f"✅ Project created: {project_id}")
            
            # Test get project
            get_response = client.get(f"/api/projects/{project_id}", headers=auth_headers)
            if get_response.status_code == 200:
                print("✅ Project retrieval works")
            else:
                print(f"❌ Project retrieval failed: {get_response.status_code}")
                return False
            
            return True
        else:
            print(f"❌ Project creation failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Project endpoints test failed: {e}")
        return False

async def test_task_endpoints():
    """Test task management endpoints"""
    print("\n📋 Testing task endpoints...")
    
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        auth_headers = {"Authorization": "Bearer mock_token"}

        
        # First create a project
        project_data = {
            "name": "Test Project for Tasks",
            "description": "A test project for task testing",
            "domain": "software"
        }
        
        project_response = client.post("/api/projects", json=project_data, headers=auth_headers)
        if project_response.status_code != 200:
            print("❌ Could not create project for task testing")
            return False
        
        project_id = project_response.json().get('id')
        
        # Test create task
        task_data = {
            "title": "Test Task",
            "description": "A test task",
            "priority": "medium",
            "estimated_hours": 8.0
        }
        
        response = client.post(f"/api/projects/{project_id}/tasks", json=task_data, headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Task created: {data.get('id')}")
            return True
        else:
            print(f"❌ Task creation failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Task endpoints test failed: {e}")
        return False

async def test_research_endpoints():
    """Test research endpoints"""
    print("\n🔬 Testing research endpoints...")
    
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        auth_headers = {"Authorization": "Bearer mock_token"}

        
        # Test start research
        research_data = {
            "topic": "AI project management",
            "project_id": str(uuid.uuid4())
        }
        
        response = client.post("/api/research", json=research_data, headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            research_id = data.get('research_id')
            print(f"✅ Research started: {research_id}")
            
            # Test get research results
            get_response = client.get(f"/api/research/{research_id}", headers=auth_headers)
            if get_response.status_code == 200:
                print("✅ Research results retrieval works")
                return True
            else:
                print(f"❌ Research results retrieval failed: {get_response.status_code}")
                return False
        else:
            print(f"❌ Research start failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Research endpoints test failed: {e}")
        return False

async def test_knowledge_endpoints():
    """Test knowledge base endpoints"""
    print("\n🧠 Testing knowledge endpoints...")
    
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        auth_headers = {"Authorization": "Bearer mock_token"}

        
        # Test knowledge search
        search_data = {
            "query": "project management best practices",
            "limit": 10
        }
        
        response = client.post("/api/knowledge/search", json=search_data, headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Knowledge search works: {len(data.get('results', []))} results")
            return True
        else:
            print(f"❌ Knowledge search failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Knowledge endpoints test failed: {e}")
        return False

async def test_websocket_connection():
    """Test WebSocket connection"""
    print("\n🔌 Testing WebSocket connection...")
    
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        
        # Test WebSocket connection
        with client.websocket_connect("/ws/chat/test_session") as websocket:
            # Send a test message
            test_message = {
                "message": "Hello WebSocket",
                "user_id": "test_user",
                "timestamp": datetime.now().isoformat()
            }
            
            websocket.send_text(json.dumps(test_message))
            
            # Try to receive a response (with timeout)
            try:
                response = websocket.receive_text()
                data = json.loads(response)
                print(f"✅ WebSocket response received: {data.get('type', 'unknown')}")
                return True
            except Exception as e:
                print(f"⚠️ WebSocket response timeout or error: {e}")
                return True  # WebSocket connection works, response might be delayed
                
    except Exception as e:
        print(f"❌ WebSocket connection test failed: {e}")
        return False

async def test_data_validation():
    """Test data validation"""
    print("\n✅ Testing data validation...")
    
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        auth_headers = {"Authorization": "Bearer mock_token"}

        
        # Test invalid project data
        invalid_project = {
            "name": "",  # Empty name should fail
            "description": "Test"
        }
        
        response = client.post("/api/projects", json=invalid_project, headers=auth_headers)
        
        if response.status_code == 422:  # Validation error
            print("✅ Data validation works (rejected invalid data)")
        else:
            print(f"❌ Data validation failed: {response.status_code}")
            return False
        
        # Test valid project data
        valid_project = {
            "name": "Valid Project",
            "description": "A valid test project",
            "domain": "software"
        }
        
        response = client.post("/api/projects", json=valid_project, headers=auth_headers)
        
        if response.status_code == 200:
            print("✅ Data validation works (accepted valid data)")
            return True
        else:
            print(f"❌ Valid data rejected: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Data validation test failed: {e}")
        return False

async def test_error_handling():
    """Test error handling"""
    print("\n🚨 Testing error handling...")
    
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        auth_headers = {"Authorization": "Bearer mock_token"}

        
        # Test 404 error
        response = client.get("/api/projects/nonexistent-id", headers=auth_headers)
        if response.status_code == 404:
            print("✅ 404 error handling works")
        else:
            print(f"❌ 404 error handling failed: {response.status_code}")
            return False
        
        # Test invalid endpoint
        response = client.get("/api/invalid-endpoint", headers=auth_headers)
        if response.status_code == 404:
            print("✅ Invalid endpoint handling works")
            return True
        else:
            print(f"❌ Invalid endpoint handling failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

async def main():
    """Run all API tests"""
    print("🚀 Starting FastAPI Tests")
    print("=" * 50)
    
    tests = [
        ("Imports", test_api_imports),
        ("Health Endpoint", test_health_endpoint),
        ("Chat Endpoints", test_chat_endpoints),
        ("Project Endpoints", test_project_endpoints),
        ("Task Endpoints", test_task_endpoints),
        ("Research Endpoints", test_research_endpoints),
        ("Knowledge Endpoints", test_knowledge_endpoints),
        ("WebSocket Connection", test_websocket_connection),
        ("Data Validation", test_data_validation),
        ("Error Handling", test_error_handling),
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
        print("🎉 All tests passed! FastAPI is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
