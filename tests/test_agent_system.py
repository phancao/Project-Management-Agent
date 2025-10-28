#!/usr/bin/env python3
"""
Test script for the complete agent system
Tests integrated DeerFlow + Project Management Agents
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.deerflow_integration import deerflow_pm_integration
from src.agents.pm_agent_manager import AgentType, AgentContext
from src.agents.tools import pm_tools
from src.utils.logger import get_logger


logger = get_logger(__name__)


async def test_agent_capabilities():
    """Test agent capabilities listing"""
    print("Testing Agent Capabilities...")
    
    try:
        capabilities = await deerflow_pm_integration.get_agent_capabilities()
        
        print("Agent Capabilities:")
        print(f"   PM Agents: {len(capabilities['project_management_agents'])}")
        print(f"   DeerFlow: {len(capabilities['deerflow_capabilities'])}")
        print(f"   Integration Features: {len(capabilities['integration_features'])}")
        
        for agent in capabilities['project_management_agents']:
            print(f"   - {agent['type']}: {agent['capability']}")
        
        return True
        
    except Exception as e:
        print(f"Agent capabilities test failed: {e}")
        return False


async def test_project_management_tools():
    """Test project management tools"""
    print("\nTesting Project Management Tools...")
    
    try:
        # Test project creation
        project_result = await pm_tools.create_project(
            name="Test Project",
            description="A test project for agent system",
            owner="test_user",
            team_members=["user1", "user2"]
        )
        
        print(f"Project created: {project_result['project_id']}")
        
        # Test task creation
        task_result = await pm_tools.create_task(
            project_id=project_result['project_id'],
            title="Test Task",
            description="A test task",
            assignee="user1",
            priority="high"
        )
        
        print(f"Task created: {task_result['task_id']}")
        
        # Test project progress
        progress_result = await pm_tools.get_project_progress(project_result['project_id'])
        print(f"Project progress: {progress_result['progress']['progress_percentage']}%")
        
        # Test risk assessment
        risk_result = await pm_tools.assess_project_risks(project_result['project_id'])
        print(f"Risk assessment: {len(risk_result['risks'])} risks identified")
        
        return True
        
    except Exception as e:
        print(f"Project management tools test failed: {e}")
        return False


async def test_agent_routing():
    """Test agent routing based on user input"""
    print("\nTesting Agent Routing...")
    
    try:
        context = AgentContext(user_id="test_user", project_id="test_project")
        
        # Test different types of requests
        test_cases = [
            ("Create a new project plan", "project_planning"),
            ("Assign this task to Alice", "task_management"),
            ("Schedule a team meeting", "team_coordination"),
            ("What are the project risks?", "risk_assessment"),
            ("Show me project progress", "progress_tracking")
        ]
        
        for user_input, expected_type in test_cases:
            result = await deerflow_pm_integration.process_request(
                user_input=user_input,
                user_id="test_user",
                project_id="test_project"
            )
            
            print(f"'{user_input}' -> {result['type']}")
        
        return True
        
    except Exception as e:
        print(f"Agent routing test failed: {e}")
        return False


async def test_research_integration():
    """Test research integration with DeerFlow"""
    print("\nTesting Research Integration...")
    
    try:
        # Test research request
        result = await deerflow_pm_integration.process_request(
            user_input="Research best practices for agile project management",
            user_id="test_user"
        )
        
        print(f"Research request processed: {result['type']}")
        
        if result['type'] == 'research_and_planning':
            research = result.get('research', {})
            pm = result.get('project_management', {})
            
            print(f"   Research success: {research.get('success', False)}")
            print(f"   PM agent type: {pm.get('agent_type', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"Research integration test failed: {e}")
        return False


async def test_project_creation_with_research():
    """Test project creation with integrated research"""
    print("\nTesting Project Creation with Research...")
    
    try:
        result = await deerflow_pm_integration.create_project_with_research(
            project_description="AI-powered mobile app development",
            user_id="test_user",
            research_requirements=[
                "mobile app development best practices",
                "AI integration in mobile apps",
                "project management for mobile development"
            ]
        )
        
        print(f"Project creation with research: {result['success']}")
        print(f"   Project ID: {result['project']['project_id']}")
        print(f"   Research results: {len(result['research'])} topics researched")
        
        return True
        
    except Exception as e:
        print(f"Project creation with research test failed: {e}")
        return False


async def test_conversation_flow():
    """Test conversation flow with agents"""
    print("\nTesting Conversation Flow...")
    
    try:
        context = AgentContext(user_id="test_user")
        
        # Simulate a conversation
        conversation_steps = [
            "I want to start a new project",
            "It's a web application for e-commerce",
            "What are the main tasks I need to do?",
            "How should I organize my team?",
            "What risks should I be aware of?"
        ]
        
        for step, user_input in enumerate(conversation_steps, 1):
            result = await deerflow_pm_integration.process_request(
                user_input=user_input,
                user_id="test_user"
            )
            
            print(f"Step {step}: {user_input}")
            print(f"   Response type: {result['type']}")
            
            # Add to conversation history
            context.conversation_history.append({
                "role": "user",
                "content": user_input
            })
            context.conversation_history.append({
                "role": "assistant",
                "content": result.get('project_management', {}).get('response', 'No response')
            })
        
        return True
        
    except Exception as e:
        print(f"Conversation flow test failed: {e}")
        return False


async def run_all_tests():
    """Run all agent system tests"""
    print("Starting Agent System Tests...")
    print("=" * 50)
    
    tests = [
        ("Agent Capabilities", test_agent_capabilities),
        ("Project Management Tools", test_project_management_tools),
        ("Agent Routing", test_agent_routing),
        ("Research Integration", test_research_integration),
        ("Project Creation with Research", test_project_creation_with_research),
        ("Conversation Flow", test_conversation_flow)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"FAIL {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"   {status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests passed! Agent system is working correctly.")
    else:
        print("Some tests failed. Check the logs above for details.")
    
    return passed == total


if __name__ == "__main__":
    asyncio.run(run_all_tests())
