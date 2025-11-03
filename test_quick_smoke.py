#!/usr/bin/env python3
"""
Quick smoke test to verify basic functionality
"""
import asyncio
from src.pm_providers import build_pm_provider
from src.conversation.flow_manager import ConversationFlowManager

async def quick_test():
    print("🧪 Quick Smoke Test")
    print("="*60)
    
    # Test 1: PM Provider initialization
    print("\n1. Testing PM Provider...")
    flow_manager = ConversationFlowManager()
    if flow_manager.pm_provider:
        print(f"   ✅ PM Provider: {flow_manager.pm_provider.__class__.__name__}")
    else:
        print("   ❌ No PM provider initialized")
        return False
    
    # Test 2: List projects
    print("\n2. Testing List Projects...")
    result = await flow_manager.process_message(
        session_id="smoke_test",
        message="list all projects"
    )
    if isinstance(result, dict) and result.get('message'):
        print("   ✅ List Projects works")
    else:
        print("   ❌ List Projects failed")
        return False
    
    print("\n✅ All smoke tests passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    exit(0 if success else 1)

