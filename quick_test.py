#!/usr/bin/env python3
"""
Quick test script for Project Management Agent
Runs essential tests to verify system functionality
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

async def quick_deerflow_test():
    """Quick DeerFlow test"""
    print("🦌 Quick DeerFlow Test...")
    
    try:
        # Test imports
        from src.llms.llm import get_llm_by_type
        from src.graph.builder import build_graph
        from src.workflow import run_agent_workflow_async
        
        # Test LLM connection
        llm = get_llm_by_type("basic_model")
        response = await llm.ainvoke("Hello")
        
        if response and response.content:
            print("✅ DeerFlow LLM connection works")
            return True
        else:
            print("❌ DeerFlow LLM connection failed")
            return False
            
    except Exception as e:
        print(f"❌ DeerFlow test failed: {e}")
        return False

async def quick_conversation_test():
    """Quick conversation flow test"""
    print("💬 Quick Conversation Test...")
    
    try:
        from src.conversation.flow_manager import ConversationFlowManager
        
        manager = ConversationFlowManager()
        response = await manager.process_message(
            message="Hello",
            session_id="test_session",
            user_id="test_user"
        )
        
        if response and 'type' in response:
            print("✅ Conversation flow manager works")
            return True
        else:
            print("❌ Conversation flow manager failed")
            return False
            
    except Exception as e:
        print(f"❌ Conversation test failed: {e}")
        return False

async def quick_api_test():
    """Quick API test"""
    print("🔌 Quick API Test...")
    
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/health")
        
        if response.status_code == 200:
            print("✅ API health check works")
            return True
        else:
            print("❌ API health check failed")
            return False
            
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

async def quick_database_test():
    """Quick database test"""
    print("🗄️ Quick Database Test...")
    
    try:
        from database.models import User, Project
        
        # Test model creation
        user = User(
            email="test@example.com",
            name="Test User",
            role="developer"
        )
        
        project = Project(
            name="Test Project",
            created_by=user.id
        )
        
        if user.id and project.id:
            print("✅ Database models work")
            return True
        else:
            print("❌ Database models failed")
            return False
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

async def main():
    """Run quick tests"""
    print("⚡ Project Management Agent - Quick Test")
    print("=" * 50)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("DeerFlow", quick_deerflow_test),
        ("Conversation", quick_conversation_test),
        ("Database", quick_database_test),
        ("API", quick_api_test),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 QUICK TEST SUMMARY")
    print(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if passed == total:
        print("\n🎉 All quick tests passed! System is ready.")
        return True
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Run full tests for details.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
