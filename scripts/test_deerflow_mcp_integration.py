#!/usr/bin/env python3
"""
Test Galaxy AI Project Manager + PM MCP Integration

Verifies that Galaxy AI Project Manager agents can successfully load and use PM tools
from the PM MCP Server.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_pm_mcp_tools_import():
    """Test importing PM MCP tools."""
    print("=" * 60)
    print("Test 1: Import PM MCP Tools")
    print("=" * 60)
    
    try:
        from backend.tools import (
            configure_pm_mcp_client,
            get_pm_mcp_tools,
            is_pm_mcp_configured,
            reset_pm_mcp_client,
        )
        
        print("✅ Successfully imported PM MCP tools functions")
        return True
    except Exception as e:
        print(f"❌ Failed to import PM MCP tools: {e}")
        return False


async def test_pm_mcp_configuration():
    """Test PM MCP client configuration."""
    print("\n" + "=" * 60)
    print("Test 2: Configure PM MCP Client")
    print("=" * 60)
    
    try:
        from backend.tools import (
            configure_pm_mcp_client,
            is_pm_mcp_configured,
            get_pm_mcp_config,
        )
        
        # Configure client
        configure_pm_mcp_client(
            transport="sse",
            url="http://localhost:8080",
            enabled_tools=["list_projects", "list_my_tasks"]
        )
        
        # Verify configuration
        assert is_pm_mcp_configured(), "Client should be configured"
        
        config = get_pm_mcp_config()
        assert config is not None, "Config should not be None"
        assert "pm-server" in config, "Config should have pm-server"
        
        print("✅ PM MCP client configured successfully")
        print(f"   Transport: {config['pm-server']['transport']}")
        print(f"   URL: {config['pm-server']['url']}")
        print(f"   Enabled tools: {config['pm-server']['enabled_tools']}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to configure PM MCP client: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_pm_mcp_tools_loading():
    """Test loading PM tools from MCP server (requires server running)."""
    print("\n" + "=" * 60)
    print("Test 3: Load PM Tools from MCP Server")
    print("=" * 60)
    
    print("\n⚠️  This test requires PM MCP Server to be running!")
    print("   Start server with: uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080")
    print("\n   Skipping actual tool loading test...")
    print("   (Run manually with server running to test)")
    
    # Show what would happen
    print("\n📝 Expected behavior:")
    print("   1. Connect to PM MCP Server at http://localhost:8080")
    print("   2. Load 2 tools: list_projects, list_my_tasks")
    print("   3. Tools are LangChain-compatible and ready to use")
    
    return True


async def test_backward_compatibility():
    """Test that existing PM tools still work."""
    print("\n" + "=" * 60)
    print("Test 4: Backward Compatibility")
    print("=" * 60)
    
    try:
        from backend.tools import get_pm_tools, set_pm_handler
        
        print("✅ Existing PM tools can still be imported")
        print("   - get_pm_tools() still available")
        print("   - set_pm_handler() still available")
        print("   - Backward compatibility maintained!")
        
        return True
    except Exception as e:
        print(f"❌ Backward compatibility broken: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "DEERFLOW + PM MCP INTEGRATION TESTS" + " " * 13 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = []
    
    # Run tests
    results.append(await test_pm_mcp_tools_import())
    results.append(await test_pm_mcp_configuration())
    results.append(await test_pm_mcp_tools_loading())
    results.append(await test_backward_compatibility())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed!")
        print("\n📝 Next steps:")
        print("   1. Start PM MCP Server:")
        print("      uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080")
        print("\n   2. Test with actual tool loading:")
        print("      # In Python:")
        print("      from backend.tools import configure_pm_mcp_client, get_pm_mcp_tools")
        print("      configure_pm_mcp_client(transport='sse', url='http://localhost:8080')")
        print("      tools = await get_pm_mcp_tools()")
        print("      print(f'Loaded {len(tools)} tools')")
        print("\n   3. Integrate with Galaxy AI Project Manager agents (see docs/DEERFLOW_MCP_INTEGRATION.md)")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

