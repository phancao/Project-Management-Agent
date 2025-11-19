#!/usr/bin/env python3
"""
Test PM MCP Server in Docker

Tests the PM MCP Server running in Docker via SSE transport.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.client.sse import sse_client
from mcp import ClientSession
from datetime import timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_mcp_server_connection():
    """Test connection to PM MCP Server in Docker."""
    print("=" * 60)
    print("Testing PM MCP Server in Docker")
    print("=" * 60)
    
    # Docker service URL (from inside Docker network)
    # For local testing, use localhost
    url = "http://localhost:8080/sse"
    
    print(f"\nConnecting to: {url}")
    
    try:
        async with sse_client(url=url, timeout=30) as (read, write):
            async with ClientSession(
                read, write, read_timeout_seconds=timedelta(seconds=30)
            ) as session:
                print("✅ Connected to MCP server")
                
                # Initialize
                print("\nInitializing session...")
                await session.initialize()
                print("✅ Session initialized")
                
                # List tools
                print("\nListing tools...")
                result = await session.list_tools()
                tools = result.tools
                
                print(f"✅ Found {len(tools)} tools")
                
                if tools:
                    print("\nFirst 10 tools:")
                    for i, tool in enumerate(tools[:10], 1):
                        print(f"  {i}. {tool.name}")
                        if tool.description:
                            desc = tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
                            print(f"     {desc}")
                
                # Test a simple tool call
                if tools:
                    test_tool = tools[0]
                    print(f"\nTesting tool: {test_tool.name}")
                    print(f"  Description: {test_tool.description}")
                    
                    # Try to call the tool with empty arguments
                    try:
                        result = await session.call_tool(test_tool.name, {})
                        print(f"✅ Tool call successful")
                        print(f"  Result type: {type(result)}")
                        if hasattr(result, 'content'):
                            print(f"  Content items: {len(result.content)}")
                            if result.content:
                                print(f"  First content: {result.content[0]}")
                    except Exception as e:
                        print(f"⚠️  Tool call failed (expected for some tools): {e}")
                
                return True
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_health_endpoint():
    """Test health endpoint."""
    import httpx
    
    print("\n" + "=" * 60)
    print("Testing Health Endpoint")
    print("=" * 60)
    
    url = "http://localhost:8080/health"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                print("✅ Health check passed")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


async def test_list_tools_endpoint():
    """Test list tools endpoint."""
    import httpx
    
    print("\n" + "=" * 60)
    print("Testing List Tools Endpoint")
    print("=" * 60)
    
    url = "http://localhost:8080/tools/list"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json={})
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                tools = data.get("tools", [])
                print(f"✅ Found {len(tools)} tools via HTTP endpoint")
                
                if tools:
                    print("\nFirst 10 tools:")
                    for i, tool in enumerate(tools[:10], 1):
                        name = tool.get("name", "unknown")
                        desc = tool.get("description", "")[:60]
                        print(f"  {i}. {name}")
                        if desc:
                            print(f"     {desc}...")
                
                return True
            else:
                print(f"❌ List tools failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
    except Exception as e:
        print(f"❌ List tools failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "PM MCP SERVER DOCKER TESTS" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = []
    
    # Test health endpoint
    results.append(await test_health_endpoint())
    
    # Test list tools endpoint
    results.append(await test_list_tools_endpoint())
    
    # Test MCP client connection
    results.append(await test_mcp_server_connection())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed!")
        print("   PM MCP Server is working correctly in Docker!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

