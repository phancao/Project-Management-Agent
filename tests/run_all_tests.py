#!/usr/bin/env python3
"""
Master test script that runs all test suites
Tests the entire Project Management Agent system
"""

import asyncio
import sys
import os
import subprocess
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

async def run_test_suite(test_name, test_file):
    """Run a single test suite"""
    print(f"\n{'='*60}")
    print(f"🧪 Running {test_name}")
    print(f"{'='*60}")
    
    try:
        # Run the test file
        result = subprocess.run([
            sys.executable, test_file
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ {test_name} PASSED")
            return True
        else:
            print(f"❌ {test_name} FAILED")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {test_name} TIMED OUT")
        return False
    except Exception as e:
        print(f"💥 {test_name} CRASHED: {e}")
        return False

async def check_dependencies():
    """Check if all dependencies are available"""
    print("🔍 Checking dependencies...")
    
    dependencies = [
        ("uv", "uv --version"),
        ("python", "python --version"),
        ("node", "node --version"),
        ("npm", "npm --version"),
    ]
    
    missing = []
    
    for dep, cmd in dependencies:
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✅ {dep}: {version}")
            else:
                print(f"❌ {dep}: Not found")
                missing.append(dep)
        except:
            print(f"❌ {dep}: Not found")
            missing.append(dep)
    
    if missing:
        print(f"\n⚠️ Missing dependencies: {', '.join(missing)}")
        print("Please install missing dependencies before running tests.")
        return False
    
    return True

async def setup_environment():
    """Setup test environment"""
    print("\n🔧 Setting up test environment...")
    
    try:
        # Install Python dependencies
        print("Installing Python dependencies...")
        result = subprocess.run([
            "uv", "sync"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Python dependencies installed")
        else:
            print(f"❌ Failed to install Python dependencies: {result.stderr}")
            return False
        
        # Check if conf.yaml exists and has valid API key
        if os.path.exists("conf.yaml"):
            print("✅ Configuration file found")
        else:
            print("❌ Configuration file not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Environment setup failed: {e}")
        return False

async def main():
    """Run all test suites"""
    print("🚀 Project Management Agent - Master Test Suite")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check dependencies
    if not await check_dependencies():
        print("\n❌ Dependency check failed. Please install missing dependencies.")
        return False
    
    # Setup environment
    if not await setup_environment():
        print("\n❌ Environment setup failed.")
        return False
    
    # Define test suites
    test_suites = [
        ("Galaxy AI Project Manager Integration", "tests/backend/test_deerflow.py"),
        ("Conversation Flow Manager", "tests/backend/test_conversation_flow.py"),
        ("Database Models", "tests/shared/test_database.py"),
        ("FastAPI Endpoints", "tests/backend/test_api.py"),
        ("PM Features", "tests/pm_providers/test_pm_features.py"),
    ]
    
    # Run test suites
    results = []
    
    for test_name, test_file in test_suites:
        if os.path.exists(test_file):
            success = await run_test_suite(test_name, test_file)
            results.append((test_name, success))
        else:
            print(f"⚠️ Test file not found: {test_file}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 MASTER TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Overall Results: {passed}/{total} test suites passed")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! The system is working correctly.")
        print("\nNext steps:")
        print("1. Start the development server: docker-compose up")
        print("2. Access the frontend: http://localhost:3000")
        print("3. Access the API docs: http://localhost:8000/docs")
        return True
    else:
        print(f"\n⚠️ {total - passed} test suite(s) failed.")
        print("Please check the errors above and fix them before proceeding.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
