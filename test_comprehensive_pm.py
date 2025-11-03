#!/usr/bin/env python3
"""
Comprehensive PM Feature Testing Script

Tests all PM features systematically to ensure everything works before refactoring.
"""
import asyncio
import json
from datetime import datetime
from src.conversation.flow_manager import ConversationFlowManager
from src.config.configuration import Configuration

async def test_feature(name: str, test_func):
    """Run a single test and report results"""
    print(f"\n{'='*60}")
    print(f"🧪 Testing: {name}")
    print('='*60)
    try:
        result = await test_func()
        if result:
            print(f"✅ {name}: PASSED")
            return True
        else:
            print(f"❌ {name}: FAILED (returned False)")
            return False
    except Exception as e:
        print(f"❌ {name}: FAILED with error")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_list_projects():
    """Test listing all projects"""
    flow_manager = ConversationFlowManager()
    session_id = f"test_{datetime.now().timestamp()}"
    
    result = await flow_manager.process_message(
        session_id=session_id,
        message="liệt kê tất cả dự án"
    )
    result_str = result.get('message', '') if isinstance(result, dict) else str(result)
    return "projects" in result_str.lower() or "dự án" in result_str.lower() or len(result_str) > 50

async def test_list_my_tasks():
    """Test listing my tasks"""
    flow_manager = ConversationFlowManager()
    session_id = f"test_{datetime.now().timestamp()}"
    
    result = await flow_manager.process_message(
        session_id=session_id,
        message="tôi có những task nào"
    )
    result_str = result.get('message', '') if isinstance(result, dict) else str(result)
    return len(result_str) > 20 and ("task" in result_str.lower() or "nhiệm vụ" in result_str.lower())

async def test_switch_project():
    """Test switching to a project"""
    flow_manager = ConversationFlowManager()
    session_id = f"test_{datetime.now().timestamp()}"
    
    # First list projects to get a project name
    result1 = await flow_manager.process_message(
        session_id=session_id,
        message="liệt kê tất cả dự án"
    )
    
    # Then switch to a project (will use the project from context or first one found)
    result2 = await flow_manager.process_message(
        session_id=session_id,
        message="làm việc với dự án Scrum"
    )
    result2_str = result2.get('message', '') if isinstance(result2, dict) else str(result2)
    return "scrum" in result2_str.lower() or "switched" in result2_str.lower()

async def test_time_tracking():
    """Test time tracking"""
    flow_manager = ConversationFlowManager()
    session_id = f"test_{datetime.now().timestamp()}"
    
    result = await flow_manager.process_message(
        session_id=session_id,
        message="log 2 giờ làm việc cho task 'Setup development environment'"
    )
    result_str = result.get('message', '') if isinstance(result, dict) else str(result)
    return "logged" in result_str.lower() or "đã log" in result_str.lower() or "thành công" in result_str.lower()

async def test_team_assignments():
    """Test team assignments"""
    flow_manager = ConversationFlowManager()
    session_id = f"test_{datetime.now().timestamp()}"
    
    result = await flow_manager.process_message(
        session_id=session_id,
        message="cho tôi xem phân công công việc của team trong dự án Scrum"
    )
    result_str = result.get('message', '') if isinstance(result, dict) else str(result)
    return "assign" in result_str.lower() or "phân công" in result_str.lower() or "team" in result_str.lower()

async def test_burndown_chart():
    """Test burndown chart"""
    flow_manager = ConversationFlowManager()
    session_id = f"test_{datetime.now().timestamp()}"
    
    result = await flow_manager.process_message(
        session_id=session_id,
        message="cho tôi xem burndown chart của sprint 1"
    )
    result_str = result.get('message', '') if isinstance(result, dict) else str(result)
    return "burndown" in result_str.lower() or "progress" in result_str.lower() or "velocity" in result_str.lower()

async def test_list_all_tasks_in_project():
    """Test listing all tasks in a project"""
    flow_manager = ConversationFlowManager()
    session_id = f"test_{datetime.now().timestamp()}"
    
    result = await flow_manager.process_message(
        session_id=session_id,
        message="liệt kê tất cả task trong dự án Scrum"
    )
    result_str = result.get('message', '') if isinstance(result, dict) else str(result)
    return len(result_str) > 50

async def test_eta_research():
    """Test ETA research and update"""
    flow_manager = ConversationFlowManager()
    session_id = f"test_{datetime.now().timestamp()}"
    
    result = await flow_manager.process_message(
        session_id=session_id,
        message="giúp tôi ETA các task của tôi"
    )
    result_str = result.get('message', '') if isinstance(result, dict) else str(result)
    return len(result_str) > 100

async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🚀 COMPREHENSIVE PM FEATURE TESTING")
    print("="*60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    tests = [
        ("List All Projects", test_list_projects),
        ("List My Tasks", test_list_my_tasks),
        ("Switch Project", test_switch_project),
        ("List All Tasks in Project", test_list_all_tasks_in_project),
        ("ETA Research", test_eta_research),
        ("Team Assignments", test_team_assignments),
        ("Time Tracking", test_time_tracking),
        ("Burndown Chart", test_burndown_chart),
    ]
    
    results = []
    for name, test_func in tests:
        result = await test_feature(name, test_func)
        results.append((name, result))
        # Small delay between tests
        await asyncio.sleep(2)
    
    # Print summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60)
    
    return passed, total

if __name__ == "__main__":
    passed, total = asyncio.run(main())
    exit(0 if passed == total else 1)

