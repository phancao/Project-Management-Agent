#!/usr/bin/env python3
"""Test list_projects tool directly."""
import asyncio
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.client.sse import sse_client
from mcp import ClientSession
from datetime import timedelta


async def list_projects():
    """Call list_projects tool and display results."""
    url = "http://localhost:8080/sse"
    
    try:
        print("Connecting to PM MCP Server...")
        async with sse_client(url=url, timeout=30) as (read, write):
            async with ClientSession(
                read, write, 
                read_timeout_seconds=timedelta(seconds=30)
            ) as session:
                print("Initializing session...")
                await session.initialize()
                print("✅ Connected!\n")
                
                print("Calling list_projects tool...")
                result = await session.call_tool("list_projects", {})
                
                print("\n" + "=" * 60)
                print("PROJECTS:")
                print("=" * 60)
                
                if hasattr(result, 'content') and result.content:
                    for i, content_item in enumerate(result.content, 1):
                        if hasattr(content_item, 'text'):
                            print(f"\n[{i}] {content_item.text}")
                        else:
                            print(f"\n[{i}] {content_item}")
                else:
                    print(f"Result: {result}")
                    print(f"Result type: {type(result)}")
                    
                    # Try to serialize and print
                    try:
                        print(f"\nResult attributes: {dir(result)}")
                    except:
                        pass
                
                print("\n" + "=" * 60)
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(list_projects())










