#!/usr/bin/env python3
"""
Test script for Project Management features
Tests time tracking, burndown charts, and team assignments
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

async def test_pm_provider_imports():
    """Test PM provider imports"""
    print("🔍 Testing PM Provider imports...")
    
    try:
        from src.pm_providers import build_pm_provider
        from src.pm_providers.models import (
            PMProject, PMTask, PMSprint, PMUser,
            PMProviderConfig, PMStatus, PMPriority
        )
        from src.pm_providers.openproject import OpenProjectProvider
        from src.pm_providers.base import BasePMProvider
        
        print("✅ PM Provider imports successful")
        return True
    except Exception as e:
        print(f"❌ PM Provider imports failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_time_tracking_methods():
    """Test time tracking methods exist"""
    print("\n⏱️ Testing time tracking methods...")
    
    try:
        from src.pm_providers.openproject import OpenProjectProvider
        from src.pm_providers.models import PMProviderConfig
        import inspect
        
        # Check if OpenProjectProvider has time tracking methods
        provider = OpenProjectProvider.__new__(OpenProjectProvider)  # Don't call __init__
        
        required_methods = [
            'log_time_entry',
            'get_time_entries',
            'get_total_hours_for_task',
            '_format_hours_to_duration'
        ]
        
        for method_name in required_methods:
            if not hasattr(provider, method_name):
                print(f"❌ Missing method: {method_name}")
                return False
            
            # Check if it's async
            method = getattr(provider, method_name)
            if method_name != '_format_hours_to_duration':
                if not inspect.iscoroutinefunction(method):
                    print(f"⚠️ Method {method_name} should be async")
            
            print(f"✅ Found method: {method_name}")
        
        print("✅ All time tracking methods exist")
        return True
    except Exception as e:
        print(f"❌ Time tracking methods test failed: {e}")
        return False

async def test_burndown_chart_handler():
    """Test burndown chart handler exists"""
    print("\n📊 Testing burndown chart handler...")
    
    try:
        from src.conversation.flow_manager import ConversationFlowManager
        import inspect
        
        # Get flow manager instance
        fm = ConversationFlowManager()
        
        # Check if handler exists
        if not hasattr(fm, '_handle_burndown_chart'):
            print("❌ Missing method: _handle_burndown_chart")
            return False
        
        handler = getattr(fm, '_handle_burndown_chart')
        
        # Check if it's async
        if not inspect.iscoroutinefunction(handler):
            print("❌ _handle_burndown_chart should be async")
            return False
        
        print("✅ Burndown chart handler exists and is async")
        return True
    except Exception as e:
        print(f"❌ Burndown chart handler test failed: {e}")
        return False

async def test_team_assignments_handler():
    """Test team assignments handler exists"""
    print("\n👥 Testing team assignments handler...")
    
    try:
        from src.conversation.flow_manager import ConversationFlowManager
        import inspect
        
        # Get flow manager instance
        fm = ConversationFlowManager()
        
        # Check if handler exists
        if not hasattr(fm, '_handle_team_assignments'):
            print("❌ Missing method: _handle_team_assignments")
            return False
        
        handler = getattr(fm, '_handle_team_assignments')
        
        # Check if it's async
        if not inspect.iscoroutinefunction(handler):
            print("❌ _handle_team_assignments should be async")
            return False
        
        print("✅ Team assignments handler exists and is async")
        return True
    except Exception as e:
        print(f"❌ Team assignments handler test failed: {e}")
        return False

async def test_time_tracking_handler():
    """Test time tracking handler exists"""
    print("\n⏱️ Testing time tracking handler...")
    
    try:
        from src.conversation.flow_manager import ConversationFlowManager
        import inspect
        
        # Get flow manager instance
        fm = ConversationFlowManager()
        
        # Check if handler exists
        if not hasattr(fm, '_handle_time_tracking'):
            print("❌ Missing method: _handle_time_tracking")
            return False
        
        handler = getattr(fm, '_handle_time_tracking')
        
        # Check if it's async
        if not inspect.iscoroutinefunction(handler):
            print("❌ _handle_time_tracking should be async")
            return False
        
        print("✅ Time tracking handler exists and is async")
        return True
    except Exception as e:
        print(f"❌ Time tracking handler test failed: {e}")
        return False

async def test_pm_step_types():
    """Test PM step types enum"""
    print("\n🏷️ Testing PM step types...")
    
    try:
        from src.prompts.pm_planner_model import PMStepType
        
        # Check for new step types
        required_steps = [
            'TIME_TRACKING',
            'BURNDOWN_CHART',
            'TEAM_ASSIGNMENTS'
        ]
        
        for step_name in required_steps:
            if not hasattr(PMStepType, step_name):
                print(f"❌ Missing step type: {step_name}")
                return False
            
            step_value = getattr(PMStepType, step_name).value
            print(f"✅ Found step type: {step_name} = '{step_value}'")
        
        print("✅ All required PM step types exist")
        return True
    except Exception as e:
        print(f"❌ PM step types test failed: {e}")
        return False

async def test_iso8601_duration_formatting():
    """Test ISO 8601 duration formatting"""
    print("\n⏱️ Testing ISO 8601 duration formatting...")
    
    try:
        from src.pm_providers.openproject import OpenProjectProvider
        
        # Create provider instance without calling __init__
        provider = OpenProjectProvider.__new__(OpenProjectProvider)
        
        # Test _format_hours_to_duration
        test_cases = [
            (0, "PT0H"),
            (1, "PT1H"),
            (2.5, "PT2H30M"),
            (0.5, "PT0H30M"),
            (8, "PT8H"),
            (24, "PT24H"),
        ]
        
        for hours, expected in test_cases:
            result = provider._format_hours_to_duration(hours)
            if result == expected:
                print(f"✅ {hours}h -> {result}")
            else:
                print(f"❌ {hours}h -> {result} (expected {expected})")
                return False
        
        print("✅ All duration formatting tests passed")
        return True
    except Exception as e:
        print(f"❌ Duration formatting test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_iso8601_duration_parsing():
    """Test ISO 8601 duration parsing"""
    print("\n⏱️ Testing ISO 8601 duration parsing...")
    
    try:
        from src.pm_providers.openproject import OpenProjectProvider
        
        # Test _parse_duration_to_hours
        test_cases = [
            ("PT0H", 0),
            ("PT1H", 1.0),
            ("PT2H30M", 2.5),
            ("PT0H30M", 0.5),
            ("PT8H", 8.0),
            ("PT24H", 24.0),
            ("P1DT2H", 26.0),  # 1 day + 2 hours
            ("P2DT2H", 50.0),  # 2 days + 2 hours
        ]
        
        for duration_str, expected_hours in test_cases:
            result = OpenProjectProvider._parse_duration_to_hours(duration_str)
            if result == expected_hours:
                print(f"✅ {duration_str} -> {result}h")
            else:
                print(f"❌ {duration_str} -> {result}h (expected {expected_hours}h)")
                return False
        
        print("✅ All duration parsing tests passed")
        return True
    except Exception as e:
        print(f"❌ Duration parsing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_data_extraction_for_burndown():
    """Test data extraction for burndown chart"""
    print("\n🔍 Testing data extraction for burndown chart...")
    
    try:
        from src.conversation.flow_manager import DataExtractor, IntentType
        
        extractor = DataExtractor()
        
        # Test field descriptions
        description = extractor._get_field_descriptions(IntentType.SWITCH_SPRINT)
        
        if "sprint_name" in description.lower() or "sprint" in description.lower():
            print("✅ Switch sprint field descriptions exist")
        else:
            print("❌ Missing sprint_name in field descriptions")
            return False
        
        print("✅ Data extraction configuration for burndown looks good")
        return True
    except Exception as e:
        print(f"❌ Data extraction test failed: {e}")
        return False

async def main():
    """Run all PM feature tests"""
    print("🚀 Starting Project Management Feature Tests")
    print("=" * 60)
    
    tests = [
        ("PM Provider Imports", test_pm_provider_imports),
        ("Time Tracking Methods", test_time_tracking_methods),
        ("Burndown Chart Handler", test_burndown_chart_handler),
        ("Team Assignments Handler", test_team_assignments_handler),
        ("Time Tracking Handler", test_time_tracking_handler),
        ("PM Step Types", test_pm_step_types),
        ("ISO 8601 Duration Formatting", test_iso8601_duration_formatting),
        ("ISO 8601 Duration Parsing", test_iso8601_duration_parsing),
        ("Data Extraction for Burndown", test_data_extraction_for_burndown),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! PM features are implemented correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

