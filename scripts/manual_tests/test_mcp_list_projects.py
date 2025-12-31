#!/usr/bin/env python3
"""
Test script to call list_projects tool via MCP server

This script follows the MCP protocol fundamentals:
1. Connect to SSE endpoint
2. Initialize session (required by MCP protocol)
3. List available tools
4. Call a tool
"""
import asyncio
import sys
from pathlib import Path
from datetime import timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.client.sse import sse_client
from mcp import ClientSession


async def test_list_projects():
    """
    Test list_projects tool via MCP SSE connection.
    
    Follows MCP protocol fundamentals:
    - Uses MCP SDK's sse_client for proper SSE transport
    - Uses ClientSession for proper MCP protocol handling
    - Calls initialize() first (required by MCP protocol)
    - Then lists tools and calls a tool
    """
    url = "http://localhost:8080/sse"
    print(f"🔌 Connecting to MCP server at {url}...")
    
    try:
        # Step 1: Connect to SSE endpoint using MCP SDK's sse_client
        # This handles the SSE protocol automatically
        async with sse_client(url=url, timeout=30) as (read, write):
            # Step 2: Create ClientSession with read/write streams
            # ClientSession handles MCP protocol automatically
            async with ClientSession(
                read, 
                write, 
                read_timeout_seconds=timedelta(seconds=30)
            ) as session:
                print("✓ ClientSession created")
                
                # Step 3: Initialize the session (REQUIRED by MCP protocol)
                # This sends the initialize request and waits for initialize_result
                print("\n🔧 Initializing MCP session (required by protocol)...")
                init_result = await session.initialize()
                print(f"✓ Session initialized")
                print(f"  Server: {init_result.serverInfo.name} v{init_result.serverInfo.version}")
                print(f"  Protocol: {init_result.protocolVersion}")
                
                # Step 4: List available tools
                print("\n📋 Listing available tools...")
                tools_result = await session.list_tools()
                print(f"✓ Found {len(tools_result.tools)} tools")
                
                # Show first few tools
                tool_names = [t.name for t in tools_result.tools]
                print(f"  Tools (first 10): {', '.join(tool_names[:10])}")
                
                # Check if list_projects is available
                if "list_projects" not in tool_names:
                    print(f"\n⚠️  list_projects tool NOT found!")
                    print(f"  Available tools: {', '.join(tool_names)}")
                    return 1
                
                print(f"✓ list_projects tool is available")
                
                # Step 5: Call the list_projects tool
                print("\n🔍 Calling list_projects tool...")
                result = await session.call_tool("list_projects", {})
                
                # Display results
                print(f"\n📊 Tool call result:")
                if hasattr(result, "content"):
                    content = result.content
                    print(f"✓ Content: {len(content)} items")
                    print("\n" + "=" * 60)
                    for item in content:
                        if hasattr(item, "text"):
                            print(item.text)
                        elif hasattr(item, "type"):
                            print(f"[{item.type}]: {item}")
                        else:
                            print(f"Item: {item}")
                    print("=" * 60)
                else:
                    print(f"Result: {result}")
                
                print("\n✅ Test completed successfully!")
                return 0
                    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(test_list_projects()))
