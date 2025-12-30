#!/usr/bin/env python3
"""
Test runner script for Project Management Agent
Allows running individual test suites or all tests
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

async def run_deerflow_tests():
    """Run Galaxy AI Project Manager integration tests"""
    print("🦌 Running Galaxy AI Project Manager Integration Tests...")
    from tests.test_deerflow import main
    return await main()

async def run_conversation_tests():
    """Run Conversation Flow Manager tests"""
    print("💬 Running Conversation Flow Manager Tests...")
    from tests.test_conversation_flow import main
    return await main()

async def run_database_tests():
    """Run Database tests"""
    print("🗄️ Running Database Tests...")
    from tests.test_database import main
    return await main()

async def run_api_tests():
    """Run FastAPI tests"""
    print("🔌 Running FastAPI Tests...")
    from tests.test_api import main
    return await main()

async def run_all_tests():
    """Run all test suites"""
    print("🚀 Running All Tests...")
    from tests.run_all_tests import main
    return await main()

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Project Management Agent Test Runner")
    parser.add_argument(
        "test_suite",
        choices=["deerflow", "conversation", "database", "api", "all"],
        help="Test suite to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    print(f"🧪 Project Management Agent Test Runner")
    print(f"Test Suite: {args.test_suite}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Run selected test suite
    if args.test_suite == "deerflow":
        success = asyncio.run(run_deerflow_tests())
    elif args.test_suite == "conversation":
        success = asyncio.run(run_conversation_tests())
    elif args.test_suite == "database":
        success = asyncio.run(run_database_tests())
    elif args.test_suite == "api":
        success = asyncio.run(run_api_tests())
    elif args.test_suite == "all":
        success = asyncio.run(run_all_tests())
    else:
        print(f"❌ Unknown test suite: {args.test_suite}")
        return False
    
    print(f"\n{'='*50}")
    if success:
        print("🎉 Tests completed successfully!")
    else:
        print("❌ Tests failed!")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
