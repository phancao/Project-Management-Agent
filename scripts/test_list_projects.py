#!/usr/bin/env python3
"""Quick test script to call list_projects tool."""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.client.sse import sse_client
from mcp import ClientSession
from datetime import timedelta


async def list_projects():
    """Call list_projects tool."""
    url = "http://localhost:8080/sse"
    
    try:
        async with sse_client(url=url, timeout=30) as (read, write):
            async with ClientSession(
                read, write, 
                read_timeout_seconds=timedelta(seconds=30)
            ) as session:
                await session.initialize()
                
                print("Calling list_projects tool...")
                result = await session.call_tool("list_projects", {})
                
                if hasattr(result, 'content') and result.content:
                    for content_item in result.content:
                        if hasattr(content_item, 'text'):
                            print(content_item.text)
                else:
                    print(f"Result: {result}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(list_projects())









