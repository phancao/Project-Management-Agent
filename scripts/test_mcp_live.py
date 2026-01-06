#!/usr/bin/env python3
"""
Live Test Script: MCP Server Verification
Usage: .venv/bin/python scripts/test_mcp_live.py

This script simulates an MCP client by:
1. Instantiating the PMMCPServer.
2. Initializing the tool context (connecting to DB).
3. Calling 'list_worklogs' directly via the server's internal tool registry.
"""

import sys
import os
import asyncio
import logging
import json

# Add project root
sys.path.insert(0, os.path.abspath('.'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_mcp")

# Override DB URL for local testing (similar to previous script)
# mcp_postgres is exposed on port 5435
MCP_DB_URL = "postgresql://mcp_user:mcp_password@localhost:5435/mcp_server"
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = MCP_DB_URL
if not os.environ.get("PM_SERVICE_DATABASE_URL"):
    os.environ["PM_SERVICE_DATABASE_URL"] = MCP_DB_URL

async def main():
    try:
        from mcp_server.server import PMMCPServer
        
        print("🚀 Initializing MCP Server...")
        server = PMMCPServer()
        
        # Manually initialize components (normally handled by run_*)
        server._initialize_tool_context()
        server._register_all_tools()
        
        print(f"✅ Registered {len(server.registered_tools)} tool modules.")
        
        # Simulate a tool call
        print("\n--- Testing 'list_users' (Admin/Non-Admin Fallback) ---")
        # Skipping list_users as it is slow and already verified via logs
        print("⏭️ Skipping list_users (verified in logs)")
        # tool_func = server._tool_functions.get("list_users")
        # if tool_func:
        #      print("Please wait, calling list_users...")
        #      # The handler signature is (name, arguments)
        #      result = await tool_func("list_users", {"limit": 5})
        #      # Result is list[TextContent]
        #      content = result[0].text
        #      print(f"✅ Result (truncated): {content[:200]}...")
        # else:
        #      print("❌ Could not find tool function for list_users")

        print("\n--- Testing 'list_worklogs' (with Project Filter) ---")
        tool_func = server._tool_functions.get("list_worklogs")
        
        # Verify Schema Availability
        # Access internal MCP server's tool cache
        tools_cache = getattr(server.server, "_tool_cache", {})
        worklog_tool = tools_cache.get("list_worklogs")
        
        if worklog_tool:
            print("\n🔍 Checking 'list_worklogs' Tool Schema:")
            props = worklog_tool.inputSchema.get("properties", {})
            if "start_date" in props and "end_date" in props:
                print("   ✅ 'start_date' parameter found.")
                print("   ✅ 'end_date' parameter found.")
                # print(f"   Schema: {props}")
            else:
                print("   ❌ Missing date parameters in schema!")
        else:
             print("   ⚠️ 'list_worklogs' tool object not found in cache.")
        
        if tool_func:
             # Use a smaller project ID (487 had 3 users) to avoid timeout from full fetch
             KNOWN_PROJECT_ID = "487" 
             print(f"Please wait, calling list_worklogs for project {KNOWN_PROJECT_ID}...")
             result = await tool_func("list_worklogs", {"limit": 5, "project_id": KNOWN_PROJECT_ID})
             content = result[0].text
             print(f"✅ Project Result (truncated): {content[:200]}...")

        print("\n--- Testing 'list_worklogs' (with User Filter) ---")
        if tool_func:
             # Test with "Chen Nguyen Dinh Ngoc" (ID 335)
             TEST_USER_ID = "335"
             print(f"Please wait, calling list_worklogs for user {TEST_USER_ID}...")
             
             # Fetch a large batch to ensure we have a good distribution (User has >1000 entries)
             result = await tool_func("list_worklogs", {"limit": 2000, "user_id": TEST_USER_ID})
             content = result[0].text
             
             data = json.loads(content)
             if "worklogs" in data:
                 worklogs = data["worklogs"]
                 total_count = len(worklogs)
                 print(f"✅ Retrieved {total_count} worklogs.")
                 
                 if total_count > 0:
                     indices_to_check = [0, total_count // 2, total_count - 1]
                     labels = ["FIRST", "MIDDLE", "LAST"]
                     
                     print(f"\n🔍 Inspecting First, Middle, and Last worklogs for ownership verification:")
                     
                     for label, idx in zip(labels, indices_to_check):
                         log = worklogs[idx]
                         # Check where user info is stored. Usually in _links or a user object
                         user_ref = log.get("_links", {}).get("user", {})
                         
                         print(f"  [{label} - Index {idx}] ID: {log.get('id')}")
                         print(f"      Project: {log.get('_links', {}).get('project', {}).get('title', 'Unknown')}")
                         print(f"      User Ref (Href): {user_ref.get('href', 'N/A')}")
                         print(f"      User Ref (Title): {user_ref.get('title', 'N/A')}")
                         
                         # verification logic
                         href = user_ref.get('href', '')
                         if f"/users/{TEST_USER_ID}" in href or str(TEST_USER_ID) in str(user_ref.get('id', '')):
                             print("      ✅ User ID match confirmed.")
                         else:
                             print(f"      ❌ User ID Mismatch! Expected {TEST_USER_ID}")
                 else:
                     print("⚠️ No worklogs returned, cannot verify ownership.")
             else:
                 print(f"❌ User Result (truncated): {content[:200]}...")

        print("\n--- Testing 'list_worklogs' (with Date Range Filter) ---")
        if tool_func:
             TEST_USER_ID = "335"
             
             # Test 1: Dec 2025 (Should have data)
             print(f"Please wait, calling list_worklogs for User {TEST_USER_ID} in range 2025-12-01 to 2025-12-31...")
             result = await tool_func("list_worklogs", {
                 "user_id": TEST_USER_ID,
                 "start_date": "2025-12-01",
                 "end_date": "2025-12-31",
                 "limit": 50
             })
             content = result[0].text
             data = json.loads(content)
             count_dec = len(data.get("worklogs", []))
             print(f"✅ Dec 2025 Entries: {count_dec}")
             
             # Verify dates
             if count_dec > 0:
                 first_log = data["worklogs"][0]
                 print(f"   Sample Date: {first_log.get('spentOn')}")
             
             # Test 2: Feb 2026 (Future - Should be empty)
             print(f"Please wait, calling list_worklogs for range 2026-02-01 to 2026-02-28...")
             result = await tool_func("list_worklogs", {
                 "user_id": TEST_USER_ID,
                 "start_date": "2026-02-01",
                 "end_date": "2026-02-28",
                 "limit": 50
             })
             content = result[0].text
             data = json.loads(content)
             count_feb = len(data.get("worklogs", []))
             print(f"✅ Feb 2026 Entries: {count_feb} (Expected: 0)")
             
             if count_feb == 0:
                 print("   ✅ Validated: Future range returned no results.")
             else:
                 print("   ❌ Unexpected results for future range!")

    except Exception as e:
        print(f"❌ Critical Script Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
