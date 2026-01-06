#!/usr/bin/env python3
import asyncio
import os
import sys

# Add project root
sys.path.insert(0, os.path.abspath('.'))

# Configure env vars for MCP server
MCP_DB_URL = "postgresql://mcp_user:mcp_password@localhost:5435/mcp_server"
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = MCP_DB_URL
if not os.environ.get("PM_SERVICE_DATABASE_URL"):
    os.environ["PM_SERVICE_DATABASE_URL"] = MCP_DB_URL

async def main():
    from mcp_server.server import PMMCPServer
    server = PMMCPServer()
    server._initialize_tool_context()
    server._register_all_tools()
    
    print("Searching for users...")
    tool_func = server._tool_functions.get("list_users")
    if tool_func:
        # Get users from a project to avoid global admin requirement issues if fallback is slow
        # Using project 487 (small project) as seen before
        result = await tool_func("list_users", {"project_id": "487"})
        import json
        
        # Parse the TextContent
        content_str = result[0].text
        data = json.loads(content_str)
        
        if "users" in data:
            print(f"Found {len(data['users'])} users in project 487:")
            for user in data["users"]:
                print(f"ID: {user['id']}, Name: {user['name']}")
        else:
            print("No 'users' key in response:", content_str[:200])
            
if __name__ == "__main__":
    asyncio.run(main())
