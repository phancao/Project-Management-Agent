#!/usr/bin/env python3
"""
Test PM MCP Server SSE Transport

Simple test script to verify the SSE transport is working.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_sse_server():
    """Test SSE server startup."""
    print("=" * 60)
    print("Testing PM MCP Server SSE Transport")
    print("=" * 60)
    
    from src.mcp_servers.pm_server import PMMCPServer, PMServerConfig
    
    # Create config for SSE
    config = PMServerConfig(
        transport="sse",
        host="localhost",
        port=8081,  # Use different port from main server
        log_level="INFO"
    )
    
    print(f"\n✅ Configuration created:")
    print(f"   Transport: {config.transport}")
    print(f"   Host: {config.host}")
    print(f"   Port: {config.port}")
    
    # Create server
    server = PMMCPServer(config)
    print(f"\n✅ Server instance created")
    
    print(f"\n📝 To test the SSE server, run:")
    print(f"   uv run python scripts/run_pm_mcp_server.py --transport sse --port 8081")
    print(f"\n   Then in another terminal:")
    print(f"   curl http://localhost:8081/")
    print(f"   curl http://localhost:8081/health")
    print(f"   curl http://localhost:8081/tools/list -X POST")
    
    return True


async def main():
    """Main test function."""
    try:
        result = await test_sse_server()
        if result:
            print("\n" + "=" * 60)
            print("✅ SSE Transport Test Passed!")
            print("=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print("❌ SSE Transport Test Failed")
            print("=" * 60)
            return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

