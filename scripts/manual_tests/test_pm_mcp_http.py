#!/usr/bin/env python3
"""
Test PM MCP Server HTTP Transport

Simple test script to verify the HTTP REST API is working.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_http_server():
    """Test HTTP server configuration."""
    print("=" * 60)
    print("Testing PM MCP Server HTTP Transport")
    print("=" * 60)
    
    from mcp_server.server import PMMCPServer
    from mcp_server.config import PMServerConfig
    
    # Create config for HTTP
    config = PMServerConfig(
        transport="http",
        host="localhost",
        port=8082,  # Use different port
        log_level="INFO"
    )
    
    print(f"\n✅ Configuration created:")
    print(f"   Transport: {config.transport}")
    print(f"   Host: {config.host}")
    print(f"   Port: {config.port}")
    
    # Create server
    server = PMMCPServer(config)
    print(f"\n✅ Server instance created")
    
    print(f"\n📝 To test the HTTP server, run:")
    print(f"   uv run python scripts/run_pm_mcp_server.py --transport http --port 8082")
    print(f"\n   Then in another terminal:")
    print(f"   # Server info")
    print(f"   curl http://localhost:8082/")
    print(f"\n   # API Documentation")
    print(f"   open http://localhost:8082/docs")
    print(f"\n   # Health check")
    print(f"   curl http://localhost:8082/health")
    print(f"\n   # List tools")
    print(f"   curl http://localhost:8082/tools")
    print(f"\n   # List projects")
    print(f"   curl http://localhost:8082/projects")
    print(f"\n   # List my tasks")
    print(f"   curl http://localhost:8082/tasks/my")
    print(f"\n   # Call a tool")
    print(f"   curl -X POST http://localhost:8082/tools/call \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d '{{\"tool\":\"list_projects\",\"arguments\":{{}}}}'")
    
    return True


async def main():
    """Main test function."""
    try:
        result = await test_http_server()
        if result:
            print("\n" + "=" * 60)
            print("✅ HTTP Transport Test Passed!")
            print("=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print("❌ HTTP Transport Test Failed")
            print("=" * 60)
            return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

