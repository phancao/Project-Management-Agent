#!/usr/bin/env python3
"""
Test PM MCP Server

Simple test script to verify the PM MCP Server is working correctly.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mcp_servers.pm_server import PMMCPServer, PMServerConfig


async def test_server_initialization():
    """Test that the server can be initialized."""
    print("=" * 60)
    print("Test 1: Server Initialization")
    print("=" * 60)
    
    try:
        config = PMServerConfig(
            transport="stdio",
            log_level="INFO"
        )
        
        server = PMMCPServer(config)
        print("✅ Server initialized successfully")
        print(f"   Server name: {config.server_name}")
        print(f"   Transport: {config.transport}")
        print(f"   Database URL: {config.database_url[:50]}...")
        return True
    except Exception as e:
        print(f"❌ Server initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_pm_handler_initialization():
    """Test that PM Handler can be initialized."""
    print("\n" + "=" * 60)
    print("Test 2: PM Handler Initialization")
    print("=" * 60)
    
    try:
        config = PMServerConfig(transport="stdio", log_level="ERROR")
        server = PMMCPServer(config)
        
        # Initialize PM Handler
        server._initialize_pm_handler()
        
        if server.pm_handler:
            print("✅ PM Handler initialized successfully")
            providers = server.pm_handler._get_active_providers()
            print(f"   Active Providers: {len(providers)}")
            for provider in providers:
                print(f"   - {provider.name} ({provider.provider_type})")
            return True
        else:
            print("❌ PM Handler not initialized")
            return False
    except Exception as e:
        print(f"❌ PM Handler initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_registration():
    """Test that tools can be registered."""
    print("\n" + "=" * 60)
    print("Test 3: Tool Registration")
    print("=" * 60)
    
    try:
        config = PMServerConfig(transport="stdio", log_level="ERROR")
        server = PMMCPServer(config)
        
        # Initialize PM Handler
        server._initialize_pm_handler()
        
        # Register tools
        server._register_all_tools()
        
        print("✅ Tools registered successfully")
        print(f"   Total tool modules: {len(server.registered_tools)}")
        for tool_module in server.registered_tools:
            print(f"   - {tool_module}")
        
        # Cleanup
        server._cleanup()
        
        return True
    except Exception as e:
        print(f"❌ Tool registration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_config_validation():
    """Test configuration validation."""
    print("\n" + "=" * 60)
    print("Test 4: Configuration Validation")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Valid config
    tests_total += 1
    try:
        config = PMServerConfig(transport="stdio")
        config.validate()
        print("✅ Valid stdio config passed validation")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Valid config failed validation: {e}")
    
    # Test 2: Invalid port
    tests_total += 1
    try:
        config = PMServerConfig(transport="sse", port=99999)
        config.validate()
        print("❌ Invalid port should have failed validation")
    except ValueError:
        print("✅ Invalid port correctly rejected")
        tests_passed += 1
    
    # Test 3: Auth without secret
    tests_total += 1
    try:
        config = PMServerConfig(enable_auth=True, auth_token_secret="")
        config.validate()
        print("❌ Auth without secret should have failed validation")
    except ValueError:
        print("✅ Auth without secret correctly rejected")
        tests_passed += 1
    
    print(f"\n   Passed {tests_passed}/{tests_total} validation tests")
    return tests_passed == tests_total


async def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "PM MCP SERVER TESTS" + " " * 24 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    # Suppress logging for cleaner output
    logging.basicConfig(level=logging.ERROR)
    
    results = []
    
    # Run tests
    results.append(await test_server_initialization())
    results.append(await test_pm_handler_initialization())
    results.append(await test_tool_registration())
    results.append(await test_config_validation())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

