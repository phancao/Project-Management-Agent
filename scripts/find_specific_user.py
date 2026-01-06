#!/usr/bin/env python3
import asyncio
import os
import sys
import json

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
    
    target_name = "Chen Nguyen Dinh Ngoc"
    print(f"Searching for user: {target_name}...")
    
    tool_func = server._tool_functions.get("list_users")
    if tool_func:
        # We rely on the fallback mechanism to crawl projects if needed
        # Or if we have a project hint we could use it, but let's try global fallback first
        # Increasing limit to ensure we cover all users (previous result was ~36, but limit was default 100)
        # Wait, previous run showed "100 users returned" implying we hit a cap or there are many users
        result = await tool_func("list_users", {"limit": 1000})
        
        content_str = result[0].text
        data = json.loads(content_str)
        
        found = False
        if "users" in data:
            for user in data["users"]:
                if target_name.lower() in user['name'].lower():
                    print(f"✅ FOUND USER: ID={user['id']}, Name='{user['name']}'")
                    found = True
                    break
        
        if not found:
            print(f"❌ User '{target_name}' not found in {len(data.get('users', []))} users returned.")
            
if __name__ == "__main__":
    asyncio.run(main())
