#!/usr/bin/env python3
"""
API test with mock authentication
"""

import asyncio
import sys
import os
import json
import uuid
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

async def test_api_with_auth():
    """Test API with mock authentication"""
    print("🧪 Testing API With Mock Auth")
    print("=" * 40)
    
    try:
        # Test 1: Import
        print("1. Testing API imports...")
        from api.main import app
        from fastapi.testclient import TestClient
        print("✅ API imports successful")
        
        # Test 2: Create test client with auth headers
        print("2. Creating test client with auth...")
        client = TestClient(app)
        
        # Mock auth headers
        auth_headers = {"Authorization": "Bearer mock_token"}
        print("✅ Test client with auth created")
        
        # Test 3: Health check (no auth required)
        print("3. Testing health endpoint...")
        response = client.get("/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check: {data}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
        
        # Test 4: Chat endpoint with auth
        print("4. Testing chat endpoint with auth...")
        chat_data = {
            "message": "Hello, I want to create a new project",
            "session_id": str(uuid.uuid4()),
            "user_id": "test_user"
        }
        
        response = client.post("/api/chat", json=chat_data, headers=auth_headers)
        print(f"Chat endpoint status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Chat response: {data.get('type', 'unknown')}")
            print(f"Message: {data.get('message', 'No message')[:100]}...")
        else:
            print(f"❌ Chat endpoint failed: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
        
        # Test 5: Projects endpoint with auth
        print("5. Testing projects endpoint with auth...")
        response = client.get("/api/projects", headers=auth_headers)
        print(f"Projects endpoint status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Projects response: {len(data)} projects")
        else:
            print(f"❌ Projects endpoint failed: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
        
        # Test 6: Create project with auth
        print("6. Testing create project with auth...")
        project_data = {
            "name": "Test Project",
            "description": "A test project",
            "domain": "software",
            "timeline": "3 months",
            "team_size": 5,
            "priority": "high",
            "goals": ["Build MVP", "Test features"]
        }
        
        response = client.post("/api/projects", json=project_data, headers=auth_headers)
        print(f"Create project status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Project created: {data.get('name', 'Unknown')}")
        else:
            print(f"❌ Create project failed: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
        
        print("\n🎉 API test with auth completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_api_with_auth())
    sys.exit(0 if success else 1)
