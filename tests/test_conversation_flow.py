#!/usr/bin/env python3
"""
Test script for Conversation Flow Manager
Tests conversation flow management, intent classification, and context gathering
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

async def test_conversation_imports():
    """Test conversation flow manager imports"""
    print("🔍 Testing Conversation Flow Manager imports...")
    
    try:
        from backend.conversation.flow_manager import (
            ConversationFlowManager, 
            IntentType, 
            FlowState,
            ConversationContext,
            ProjectRequirements
        )
        print("✅ Conversation Flow Manager imports successful")
        return True
    except Exception as e:
        print(f"❌ Conversation Flow Manager imports failed: {e}")
        return False

async def test_intent_classification():
    """Test intent classification"""
    print("\n🎯 Testing intent classification...")
    
    try:
        from backend.conversation.flow_manager import IntentClassifier, IntentType
        
        classifier = IntentClassifier()
        
        test_cases = [
            ("Create a new project", IntentType.CREATE_PROJECT),
            ("Plan tasks for my project", IntentType.PLAN_TASKS),
            ("Research AI project management", IntentType.RESEARCH_TOPIC),
            ("Update my project", IntentType.UPDATE_PROJECT),
            ("What's the status?", IntentType.GET_STATUS),
            ("Help me", IntentType.HELP),
            ("Random message", IntentType.UNKNOWN),
        ]
        
        for message, expected_intent in test_cases:
            result = await classifier.classify(message)
            if result == expected_intent:
                print(f"✅ '{message}' -> {result.value}")
            else:
                print(f"❌ '{message}' -> {result.value} (expected {expected_intent.value})")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Intent classification failed: {e}")
        return False

async def test_question_generation():
    """Test question generation"""
    print("\n❓ Testing question generation...")
    
    try:
        from backend.conversation.flow_manager import QuestionGenerator, IntentType
        
        generator = QuestionGenerator()
        
        # Test project creation questions
        missing_fields = ["name", "description", "timeline"]
        gathered_data = {"domain": "software"}
        
        question = await generator.generate_question(
            IntentType.CREATE_PROJECT,
            missing_fields,
            gathered_data
        )
        
        print(f"✅ Generated question: {question}")
        
        if "name" in question.lower():
            print("✅ Question contains missing field reference")
        else:
            print("❌ Question doesn't reference missing fields")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Question generation failed: {e}")
        return False

async def test_conversation_flow():
    """Test complete conversation flow"""
    print("\n💬 Testing conversation flow...")
    
    try:
        from backend.conversation.flow_manager import ConversationFlowManager
        
        manager = ConversationFlowManager()
        session_id = str(uuid.uuid4())
        
        # Test conversation sequence
        test_messages = [
            "I want to create a new project",
            "It's a software project for e-commerce",
            "The project name is 'Online Store'",
            "We need to finish it in 3 months",
            "Our team has 5 developers"
        ]
        
        for i, message in enumerate(test_messages):
            print(f"\n--- Message {i+1}: '{message}' ---")
            
            response = await manager.process_message(
                message=message,
                session_id=session_id,
                user_id="test_user"
            )
            
            print(f"Response type: {response.get('type', 'unknown')}")
            print(f"Message: {response.get('message', 'No message')}")
            print(f"State: {response.get('state', 'unknown')}")
            print(f"Intent: {response.get('intent', 'unknown')}")
            
            if response.get('missing_fields'):
                print(f"Missing fields: {response['missing_fields']}")
        
        # Check final context
        if session_id in manager.contexts:
            context = manager.contexts[session_id]
            print(f"\nFinal context state: {context.current_state.value}")
            print(f"Final intent: {context.intent.value}")
            print(f"Gathered data: {context.gathered_data}")
            
            return True
        else:
            print("❌ No context found for session")
            return False
            
    except Exception as e:
        print(f"❌ Conversation flow failed: {e}")
        return False

async def test_data_validation():
    """Test data validation"""
    print("\n✅ Testing data validation...")
    
    try:
        from backend.conversation.flow_manager import DataValidator
        
        validator = DataValidator()
        
        # Test valid data
        valid_data = {
            "name": "Test Project",
            "timeline": "3 months",
            "team_size": "5"
        }
        
        is_valid, errors = await validator.validate_project_data(valid_data)
        if is_valid and not errors:
            print("✅ Valid data validation passed")
        else:
            print(f"❌ Valid data validation failed: {errors}")
            return False
        
        # Test invalid data
        invalid_data = {
            "name": "",  # Empty name
            "timeline": "3 months",
            "team_size": "invalid"  # Invalid number
        }
        
        is_valid, errors = await validator.validate_project_data(invalid_data)
        if not is_valid and errors:
            print(f"✅ Invalid data validation passed: {errors}")
        else:
            print("❌ Invalid data validation failed")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Data validation failed: {e}")
        return False

async def test_context_management():
    """Test context management"""
    print("\n🧠 Testing context management...")
    
    try:
        from backend.conversation.flow_manager import ConversationFlowManager
        
        manager = ConversationFlowManager()
        session_id = str(uuid.uuid4())
        
        # Test context creation
        context = manager._get_or_create_context(session_id, "test_user")
        
        if context.session_id == session_id:
            print("✅ Context created successfully")
        else:
            print("❌ Context creation failed")
            return False
        
        # Test context persistence
        context2 = manager._get_or_create_context(session_id, "test_user")
        
        if context is context2:  # Same object reference
            print("✅ Context persistence works")
        else:
            print("❌ Context persistence failed")
            return False
        
        # Test required fields
        required_fields = manager._get_required_fields_for_intent(context.intent)
        print(f"✅ Required fields for {context.intent.value}: {required_fields}")
        
        return True
    except Exception as e:
        print(f"❌ Context management failed: {e}")
        return False

async def test_flow_states():
    """Test flow state transitions"""
    print("\n🔄 Testing flow state transitions...")
    
    try:
        from backend.conversation.flow_manager import ConversationFlowManager, FlowState
        
        manager = ConversationFlowManager()
        session_id = str(uuid.uuid4())
        
        # Test initial state
        context = manager._get_or_create_context(session_id, "test_user")
        
        if context.current_state == FlowState.INTENT_DETECTION:
            print("✅ Initial state is INTENT_DETECTION")
        else:
            print(f"❌ Initial state is {context.current_state.value}")
            return False
        
        # Test state transition through conversation
        response = await manager.process_message(
            message="Create a new project",
            session_id=session_id,
            user_id="test_user"
        )
        
        context = manager.contexts[session_id]
        if context.current_state == FlowState.CONTEXT_GATHERING:
            print("✅ State transitioned to CONTEXT_GATHERING")
        else:
            print(f"❌ State is {context.current_state.value}, expected CONTEXT_GATHERING")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Flow state transitions failed: {e}")
        return False

async def main():
    """Run all conversation flow tests"""
    print("🚀 Starting Conversation Flow Manager Tests")
    print("=" * 60)
    
    tests = [
        ("Imports", test_conversation_imports),
        ("Intent Classification", test_intent_classification),
        ("Question Generation", test_question_generation),
        ("Data Validation", test_data_validation),
        ("Context Management", test_context_management),
        ("Flow State Transitions", test_flow_states),
        ("Complete Conversation Flow", test_conversation_flow),
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
        print("🎉 All tests passed! Conversation Flow Manager is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
