#!/usr/bin/env python3
"""
Test script for Galaxy AI Project Manager integration
Tests basic Galaxy AI Project Manager functionality and API connectivity
"""

import asyncio
import sys
import os
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

async def test_deerflow_imports():
    """Test Galaxy AI Project Manager imports"""
    print("🔍 Testing Galaxy AI Project Manager imports...")
    
    try:
        from backend.llms.llm import get_llm_by_type
        print("✅ LLM import successful")
    except Exception as e:
        print(f"❌ LLM import failed: {e}")
        return False
    
    try:
        from backend.graph.builder import build_graph
        print("✅ Graph builder import successful")
    except Exception as e:
        print(f"❌ Graph builder import failed: {e}")
        return False
    
    try:
        from backend.graph.types import State
        print("✅ State import successful")
    except Exception as e:
        print(f"❌ State import failed: {e}")
        return False
    
    try:
        from backend.workflow import run_agent_workflow_async
        print("✅ Workflow import successful")
    except Exception as e:
        print(f"❌ Workflow import failed: {e}")
        return False
    
    return True

async def test_llm_connection():
    """Test LLM connection"""
    print("\n🤖 Testing LLM connection...")
    
    try:
        from backend.llms.llm import get_llm_by_type
        
        llm = get_llm_by_type("basic")
        print("✅ LLM instance created")
        
        # Test simple query
        response = await llm.ainvoke("Hello, this is a test. Please respond with 'Test successful'.")
        print(f"✅ LLM response: {response.content[:100]}...")
        
        return True
    except Exception as e:
        print(f"❌ LLM connection failed: {e}")
        return False

async def test_graph_building():
    """Test graph building"""
    print("\n🏗️ Testing graph building...")
    
    try:
        from backend.graph.builder import build_graph
        
        graph = build_graph()
        print("✅ Graph built successfully")
        
        # Test graph structure
        nodes = list(graph.get_graph().nodes())
        print(f"✅ Graph has {len(nodes)} nodes: {nodes}")
        
        return True
    except Exception as e:
        print(f"❌ Graph building failed: {e}")
        return False

async def test_simple_workflow():
    """Test simple workflow execution"""
    print("\n⚡ Testing simple workflow...")
    
    try:
        from backend.workflow import run_agent_workflow_async
        
        # Test with simple query
        print("Running workflow with: 'Hello world'")
        start_time = time.time()
        
        # Run workflow with timeout
        try:
            await asyncio.wait_for(
                run_agent_workflow_async(
                    user_input="Hello world",
                    debug=True,
                    max_plan_iterations=1,
                    max_step_num=2,
                    enable_background_investigation=False
                ),
                timeout=30.0
            )
            
            end_time = time.time()
            print(f"✅ Workflow completed in {end_time - start_time:.2f} seconds")
            return True
            
        except asyncio.TimeoutError:
            print("❌ Workflow timed out after 30 seconds")
            return False
            
    except Exception as e:
        print(f"❌ Workflow execution failed: {e}")
        return False

async def test_research_workflow():
    """Test research workflow"""
    print("\n🔬 Testing research workflow...")
    
    try:
        from backend.workflow import run_agent_workflow_async
        
        # Test with research query
        print("Running research workflow with: 'Research AI project management'")
        start_time = time.time()
        
        try:
            await asyncio.wait_for(
                run_agent_workflow_async(
                    user_input="Research AI project management",
                    debug=True,
                    max_plan_iterations=1,
                    max_step_num=3,
                    enable_background_investigation=True
                ),
                timeout=60.0
            )
            
            end_time = time.time()
            print(f"✅ Research workflow completed in {end_time - start_time:.2f} seconds")
            return True
            
        except asyncio.TimeoutError:
            print("❌ Research workflow timed out after 60 seconds")
            return False
            
    except Exception as e:
        print(f"❌ Research workflow failed: {e}")
        return False

async def test_configuration():
    """Test configuration loading"""
    print("\n⚙️ Testing configuration...")
    
    try:
        import yaml
        
        with open('conf.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        print("✅ Configuration loaded successfully")
        
        # Check required fields
        if 'BASIC_MODEL' in config:
            print("✅ BASIC_MODEL configuration found")
        else:
            print("❌ BASIC_MODEL configuration missing")
            return False
        
        if 'api_key' in config['BASIC_MODEL']:
            api_key = config['BASIC_MODEL']['api_key']
            if api_key and api_key != "your_openai_api_key_here":
                print("✅ API key configured")
            else:
                print("❌ API key not properly configured")
                return False
        else:
            print("❌ API key missing from configuration")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

async def main():
    """Run all Galaxy AI Project Manager tests"""
    print("🚀 Starting Galaxy AI Project Manager Integration Tests")
    print("=" * 50)
    
    tests = [
        ("Configuration", test_configuration),
        ("Imports", test_deerflow_imports),
        ("LLM Connection", test_llm_connection),
        ("Graph Building", test_graph_building),
        ("Simple Workflow", test_simple_workflow),
        ("Research Workflow", test_research_workflow),
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
        print("🎉 All tests passed! Galaxy AI Project Manager integration is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
