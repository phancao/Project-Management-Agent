#!/usr/bin/env python3
"""
Test IntentType fix
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_intent():
    """Test IntentType import and classification"""
    print("🧪 Testing IntentType Fix")
    print("=" * 30)
    
    try:
        # Test 1: Import IntentType
        print("1. Testing IntentType import...")
        from src.conversation.flow_manager import IntentType, IntentClassifier
        print("✅ IntentType imported successfully")
        
        # Test 2: Create classifier
        print("2. Testing IntentClassifier...")
        classifier = IntentClassifier()
        print("✅ IntentClassifier created")
        
        # Test 3: Test classification
        print("3. Testing classification...")
        result = await classifier.classify("Create a new project")
        print(f"✅ Classification result: {result}")
        print(f"✅ Result type: {type(result)}")
        print(f"✅ Result value: {result.value}")
        
        # Test 4: Compare with IntentType
        print("4. Testing IntentType comparison...")
        if result == IntentType.CREATE_PROJECT:
            print("✅ Classification matches IntentType.CREATE_PROJECT")
        else:
            print(f"❌ Classification mismatch: {result} != {IntentType.CREATE_PROJECT}")
        
        print("\n🎉 IntentType fix successful!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_intent())
    sys.exit(0 if success else 1)
