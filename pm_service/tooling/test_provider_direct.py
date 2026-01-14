
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

# Set correct database URL for local testing
os.environ["PM_SERVICE_DATABASE_URL"] = "postgresql://mcp_user:mcp_password@localhost:5435/mcp_server"

from pm_service.database.connection import SessionLocal
from pm_service.handlers import PMHandler
from pm_service.providers.openproject_v13 import OpenProjectV13Provider


async def main():
    db = SessionLocal()
    try:
        handler = PMHandler(db_session=db)
        providers = handler.get_active_providers()
        
        if not providers:
            print("No active providers found.")
            return

        # Initialize V13 provider directly
        config = providers[0]
        print(f"Testing with Provider: {config.name} ({config.base_url})")
        provider = OpenProjectV13Provider(config)
        
        # Verify User
        me = await provider.get_current_user()
        print(f"Current User: {me.name} (ID: {me.id})")
        
        # Test Parameters
        TEST_PROJECT_ID = 480
        # Test Parameters
        TEST_PROJECT_ID = 480
        
        # 1. Search for specific users globally
        print(f"\n--- 1. Searching for Specific Users Globally ---")
        target_names = [
            "Cuong Nguyen Quoc",
            "Hung Nguyen Phi",
            "Luong Vo Dai",
            "Hung Do Pham Quang",
            "Trinh Huynh Ngoc",
            "Uy Nguyen Huu"
        ]
        
        found_users = {} # name -> PMUser
        
        try:
            # We need to list all users to find them by name
            # Since we can't filter by name in the API cleanly without knowing exact match or using search?
            # OpenProject API v3/users has filters but let's try listing all first (might be slow if many users)
            # The provider list_users iterates pages.
            
            print("Fetching global user list...")
            all_users_list = await provider.list_users() # Global list
            print(f"Total Global Users: {len(all_users_list)}")
            
            for user in all_users_list:
                u_name = user.name.lower()
                for target in target_names:
                    t_parts = target.lower().split()
                    # Loose matching: if all parts of target name appear in user name
                    # or if user name appears in target?
                    # Let's try exact substring match of full target
                    if target.lower() in u_name:
                         print(f"  -> FOUND: {user.name} (ID: {user.id}) matches '{target}'")
                         found_users[user.id] = user
                    elif all(part in u_name for part in t_parts):
                         print(f"  -> FOUND (Loose): {user.name} (ID: {user.id}) matches '{target}'")
                         found_users[user.id] = user
            
            if not found_users:
                print("No matching users found globally.")
                
        except Exception as e:
            print(f"Error listing global users: {e}")

        # 2. Simulate "Team Workload" Global Aggregation
        print(f"\n--- 2. Simulating Team Workload Aggregation (Global) ---")
        START_DATE = "2025-01-01"
        END_DATE = "2026-12-31"
        
        # We want to check if the HANDLER logic (or equivalent direct provider logic)
        # returns data when we ask for "User X, Y, Z" with NO Project ID.
        
        target_uids = list(found_users.keys())
        if not target_uids:
            print("Skipping step 2 as no users found.")
        else:
            print(f"Querying Worklogs for {len(target_uids)} users GLOBALLY (No Project Filter)...")
            
            # Using provider directly but mirroring Handler logic:
            # Loop through users and fetch time entries without project_id
            
            for uid in target_uids:
                user_name = found_users[uid].name
                print(f"\nFetching for User: {user_name} (ID: {uid})")
                count = 0
                sample_projects = set()
                
                try:
                    async for entry in provider.get_time_entries(
                        user_id=uid,
                        start_date=START_DATE,
                        end_date=END_DATE,
                        project_id=None # EXPLICITLY NONE
                    ):
                        count += 1
                        # Track which projects they ARE working on
                        p_link = entry.get('_links', {}).get('project', {}).get('href')
                        if p_link:
                            # Extract Project ID from href /api/v3/projects/ID
                            pid = p_link.split('/')[-1]
                            sample_projects.add(pid)
                        
                        if count >= 10: break # Just need to verify existence
                        
                    print(f"  -> Total Entries Found: {'>' if count>=10 else ''}{count}")
                    if sample_projects:
                        print(f"  -> Active in Projects: {list(sample_projects)}")
                    else:
                        print(f"  -> Active in Projects: None (or links missing)")
                        
                except Exception as e:
                    print(f"  Error fetching for {uid}: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
