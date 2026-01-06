#!/usr/bin/env python3
"""
Live Test Script: OpenProject Fallback Verification
Usage: .venv/bin/python scripts/test_fallback_live.py

This script connects to the active PM Service database, initializes the PMHandler,
filters for the 'bstarsolution' provider (if available), and tests:
1. list_users() -> Verifying fallback if non-admin
2. get_time_entries() -> Verifying fallback if non-admin
"""

import sys
import os
import asyncio
import logging

# Add project root
sys.path.insert(0, os.path.abspath('.'))

# OVERRIDE DATABASE URL FOR LOCAL EXECUTION
# The config.py has a default pointing to 'mcp-postgres'.
# Since .env doesn't have it, we must explicitly set it to localhost.
# Docker Compose maps mcp_postgres port 5432 to host port 5435
DEFAULT_DB_URL = "postgresql://mcp_user:mcp_password@localhost:5435/mcp_server"

from dotenv import load_dotenv
load_dotenv()

current_url = os.environ.get("PM_SERVICE_DATABASE_URL")
if current_url:
    # If set (e.g. from some other source), assume it might be docker inter-service URL
    os.environ["PM_SERVICE_DATABASE_URL"] = current_url.replace("mcp-postgres", "localhost")
else:
    # If not set, use our hardcoded localhost default
    os.environ["PM_SERVICE_DATABASE_URL"] = DEFAULT_DB_URL

print(f"Using Database URL: {os.environ['PM_SERVICE_DATABASE_URL']}")

# Configure logging to see our Fallback warnings
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_fallback")

async def main():
    try:
        from pm_service.database import get_db_session
        from pm_service.handlers import PMHandler
        
        # Initialize DB session
        db = next(get_db_session())
        handler = PMHandler(db)
        
        # Get active providers
        providers = handler.get_active_providers()
        print(f"Configs found: {[p.name for p in providers]}")
        
        # Filter for 'bstarsolution' or take the first one
        target_provider_conn = next((p for p in providers if "bstar" in p.name.lower()), None)
        if not target_provider_conn:
            print("⚠️ 'bstarsolution' provider not found. Using first available.")
            target_provider_conn = providers[0] if providers else None
            
        if not target_provider_conn:
            print("❌ No active providers found in database.")
            return

        print(f"\n--- Testing Provider: {target_provider_conn.name} ---")
        provider = handler.create_provider_instance(target_provider_conn)
        
        # TEST 1: List Users
        print("\n[TEST 1] Listing Users (Automatic Fallback Check)...")
        try:
            users = await provider.list_users()
            print(f"✅ Success! Found {len(users)} users.")
            # Print first 5 to verify
            for u in users[:5]:
                print(f"  - {u.name} (ID: {u.id})")
        except Exception as e:
            print(f"❌ Failed to list users: {e}")

        # TEST 2: List Worklogs
        print("\n[TEST 2] Listing Time Entries (Automatic Fallback Check)...")
        try:
            # We don't filter by user here to force the 'global' check first
            entries = await provider.get_time_entries()
            print(f"✅ Success! Found {len(entries)} time entries.")
            if entries:
                print(f"  First entry: {entries[0]}")
        except Exception as e:
            print(f"❌ Failed to list time entries: {e}")

    except Exception as e:
        print(f"❌ Critical Script Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
