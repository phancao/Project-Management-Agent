#!/usr/bin/env python3
"""
Test PM MCP Server connection for Cursor.

This script verifies that the PM MCP Server is accessible and working
correctly, which is required for Cursor to use it.

Usage:
    uv run python scripts/test_cursor_mcp_connection.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.client.sse import sse_client
from mcp import ClientSession
from datetime import timedelta


async def test_connection():
    """Test PM MCP Server connection."""
    print("=" * 60)
    print("Testing PM MCP Server Connection for Cursor")
    print("=" * 60)
    print()
    
    # Test SSE connection (for Docker/Cursor)
    url = "http://localhost:8080/sse"
    print(f"Testing connection to: {url}")
    print()
    
    try:
        print("Step 1: Connecting to server...")
        async with sse_client(url=url, timeout=30) as (read, write):
            print("✅ Connection established")
            print()
            
            print("Step 2: Creating client session...")
            async with ClientSession(
                read, write, 
                read_timeout_seconds=timedelta(seconds=30)
            ) as session:
                print("✅ Session created")
                print()
                
                print("Step 3: Initializing session...")
                await session.initialize()
                print("✅ Session initialized")
                print()
                
                print("Step 4: Listing available tools...")
                result = await session.list_tools()
                tool_count = len(result.tools)
                print(f"✅ Found {tool_count} tools")
                print()
                
                if tool_count == 0:
                    print("⚠️  WARNING: No tools found!")
                    print("   This might indicate a configuration issue.")
                    print()
                else:
                    # List first 10 tool names
                    tool_names = [tool.name for tool in result.tools[:10]]
                    print(f"   Sample tools ({min(10, tool_count)} of {tool_count}):")
                    for i, name in enumerate(tool_names, 1):
                        print(f"   {i}. {name}")
                    if tool_count > 10:
                        print(f"   ... and {tool_count - 10} more")
                    print()
                
                # Test a simple tool call
                print("Step 5: Testing tool call (list_projects)...")
                try:
                    tool_result = await session.call_tool("list_projects", {})
                    print("✅ Successfully called list_projects tool")
                    
                    # Check result type
                    if hasattr(tool_result, 'content'):
                        content_count = len(tool_result.content) if tool_result.content else 0
                        print(f"   Tool returned {content_count} content items")
                        
                        # Show first content item preview
                        if tool_result.content:
                            first_content = tool_result.content[0]
                            if hasattr(first_content, 'text'):
                                preview = first_content.text[:100] if len(first_content.text) > 100 else first_content.text
                                print(f"   Preview: {preview}...")
                    else:
                        print(f"   Tool result type: {type(tool_result)}")
                    print()
                except Exception as e:
                    print(f"⚠️  Tool call failed: {e}")
                    print("   This might be okay if there are no projects configured.")
                    print()
                
                print("=" * 60)
                print("✅ All connection tests passed!")
                print()
                print("Your PM MCP Server is ready for Cursor.")
                print()
                print("Next steps:")
                print("1. Restart Cursor if you haven't already")
                print("2. Open Cursor chat (Cmd+L / Ctrl+L)")
                print("3. Try asking: 'List all my projects'")
                print("4. Check if PM tools are being used")
                print("=" * 60)
                return True
                
    except ConnectionError as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("1. Is the PM MCP Server running?")
        print("   Check: docker-compose ps pm_mcp_server")
        print("   Or: curl http://localhost:8080/health")
        print()
        print("2. Start the server if needed:")
        print("   docker-compose up -d pm_mcp_server")
        print()
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print()
        print("Troubleshooting:")
        print("1. Check server logs:")
        print("   docker-compose logs pm_mcp_server | tail -50")
        print()
        print("2. Test health endpoint:")
        print("   curl http://localhost:8080/health")
        print()
        print("3. Verify URL is correct:")
        print(f"   Expected: {url}")
        print()
        print("4. Check Cursor MCP config:")
        print("   ~/.cursor/mcp.json or Cursor Settings → Features → MCP")
        print()
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_connection())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)











