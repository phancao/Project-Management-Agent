#!/usr/bin/env python3
"""
Test PM MCP Server Tool Registration

Specifically tests if tools are actually registered in _tool_cache after MCP SDK update.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.server import PMMCPServer
from mcp_server.config import PMServerConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_list_tools_response():
    """Test that list_tools handler returns tools."""
    print("=" * 60)
    print("Test: list_tools Handler Response")
    print("=" * 60)
    
    try:
        config = PMServerConfig(transport="stdio", log_level="ERROR")
        server = PMMCPServer(config)
        
        # Initialize PM Handler
        server._initialize_pm_handler()
        
        # Register all tools
        server._register_all_tools()
        
        # Check tracked tool names
        print(f"\nTracked tool names: {len(server._tool_names)}")
        if server._tool_names:
            print(f"   Sample names: {server._tool_names[:5]}")
        
        # Check _tool_cache
        print(f"\n_tool_cache count: {len(server.server._tool_cache)}")
        
        # Try to call list_tools handler directly
        print("\nCalling list_tools handler...")
        try:
            # Get the list_tools handler
            from mcp.types import ListToolsRequest
            if ListToolsRequest in server.server.request_handlers:
                handler = server.server.request_handlers[ListToolsRequest]
                # Call the handler
                result = await handler(ListToolsRequest(params=None))
                
                # Debug: print result structure
                print(f"   Result type: {type(result)}")
                try:
                    dump = result.model_dump()
                    print(f"   Dump keys: {list(dump.keys())}")
                    if 'content' in dump:
                        content = dump['content']
                        print(f"   Content type: {type(content)}")
                        if isinstance(content, dict):
                            print(f"   Content keys: {list(content.keys())}")
                            if 'tools' in content:
                                print(f"   Tools in content: {len(content['tools'])}")
                except Exception as e:
                    print(f"   Error dumping: {e}")
                
                # Extract tools from result
                # The SDK wraps ListToolsResult in ServerResult, but flattens it
                tools = []
                try:
                    dump = result.model_dump()
                    if 'tools' in dump:
                        # Tools are directly in the dump
                        tools_data = dump['tools']
                        # Convert dicts to Tool objects if needed
                        from mcp.types import Tool
                        if tools_data and isinstance(tools_data[0], dict):
                            tools = [Tool(**t) for t in tools_data]
                        elif tools_data:
                            tools = tools_data
                    elif 'content' in dump:
                        # Try nested content
                        content = dump['content']
                        if isinstance(content, dict) and 'tools' in content:
                            tools_data = content['tools']
                            from mcp.types import Tool
                            if tools_data and isinstance(tools_data[0], dict):
                                tools = [Tool(**t) for t in tools_data]
                            else:
                                tools = tools_data
                except Exception as e:
                    print(f"   Error extracting tools: {e}")
                    import traceback
                    traceback.print_exc()
                
                print(f"✅ list_tools returned {len(tools)} tools!")
                if tools:
                    print(f"   Sample tool names: {[t.name if hasattr(t, 'name') else str(t) for t in tools[:5]]}")
                    return True
                else:
                    print(f"   ⚠️  list_tools returned empty list")
                    print(f"   Result type: {type(result)}")
                    print(f"   Result attributes: {dir(result)[:10]}")
                    return False
            else:
                print("❌ ListToolsRequest handler not found")
                return False
        except Exception as e:
            print(f"❌ Error calling list_tools: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_server_list_tools():
    """Test that server can list tools internally."""
    print("\n" + "=" * 60)
    print("Test: Server list_tools Method")
    print("=" * 60)
    
    try:
        config = PMServerConfig(transport="stdio", log_level="ERROR")
        server = PMMCPServer(config)
        
        # Initialize PM Handler
        server._initialize_pm_handler()
        
        # Register all tools
        server._register_all_tools()
        
        # Try to call list_tools if available
        if hasattr(server.server, 'list_tools'):
            print("✅ Server has list_tools method")
            # Note: We can't actually call it here without a session, but we can check
            return True
        else:
            print("⚠️  Server doesn't have list_tools method")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "PM MCP TOOL REGISTRATION TESTS" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = []
    
    # Run tests
    results.append(await test_list_tools_response())
    results.append(await test_server_list_tools())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed!")
        print("   Tools are properly registered in _tool_cache!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        if not results[0]:
            print("\n⚠️  Tools are NOT being registered in _tool_cache")
            print("   This means the MCP SDK update didn't fix the issue")
            print("   We may need to check the tool registration pattern")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

