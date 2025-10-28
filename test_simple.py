#!/usr/bin/env python3
"""
Simple test script for DeerFlow
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_basic():
    """Test basic DeerFlow functionality"""
    print("🧪 Testing DeerFlow Basic Functionality")
    print("=" * 50)
    
    try:
        # Test 1: Import
        print("1. Testing imports...")
        from src.llms.llm import get_llm_by_type
        from src.graph.builder import build_graph
        from src.graph.types import State
        print("✅ Imports successful")
        
        # Test 2: LLM
        print("2. Testing LLM...")
        llm = get_llm_by_type("basic")
        print("✅ LLM created")
        
        # Test 3: Graph
        print("3. Testing graph...")
        graph = build_graph()
        print("✅ Graph built")
        
        # Test 4: Simple query
        print("4. Testing simple query...")
        response = await llm.ainvoke("Hello, respond with 'Test successful'")
        print(f"✅ LLM response: {response.content[:100]}...")
        
        print("\n🎉 All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_basic())
    sys.exit(0 if success else 1)
