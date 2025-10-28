#!/usr/bin/env python3
"""
Simple API test without authentication
"""

import asyncio
import sys
import os
import json
import uuid
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

async def test_api_simple():
    """Test API without authentication"""
    print("🧪 Testing API Simple (No Auth)")
    print("=" * 40)
    
    try:
        # Test 1: Import
        print("1. Testing API imports...")
        from api.main import app
        from fastapi.testclient import TestClient
        print("✅ API imports successful")
        
        # Test 2: Create test client
        print("2. Creating test client...")
        client = TestClient(app)
        print("✅ Test client created")
        
        # Test 3: Health check (no auth required)
        print("3. Testing health endpoint...")
        response = client.get("/health")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check: {data}")
        else:
            print(f"❌ Health check failed: {response.text}")
            return False
        
        # Test 4: Test endpoints that require auth (should return 403)
        print("4. Testing protected endpoints...")
        
        # Test chat endpoint
        chat_response = client.post("/api/chat", json={
            "message": "Hello",
            "session_id": str(uuid.uuid4())
        })
        print(f"Chat endpoint status: {chat_response.status_code}")
        if chat_response.status_code == 403:
            print("✅ Chat endpoint properly protected")
        else:
            print(f"❌ Chat endpoint unexpected status: {chat_response.status_code}")
        
        # Test projects endpoint
        projects_response = client.get("/api/projects")
        print(f"Projects endpoint status: {projects_response.status_code}")
        if projects_response.status_code == 403:
            print("✅ Projects endpoint properly protected")
        else:
            print(f"❌ Projects endpoint unexpected status: {projects_response.status_code}")
        
        print("\n🎉 API test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_api_simple())
    sys.exit(0 if success else 1)
