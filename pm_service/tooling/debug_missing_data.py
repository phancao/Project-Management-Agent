
import asyncio
import logging
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from pm_service.database.connection import get_db_session
from pm_service.handlers.pm_handler import PMHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_missing_data():
    db_gen = get_db_session()
    db = next(db_gen)
    
    try:
        handler = PMHandler(db_session=db)
        
        
        
        # 1. List active providers
        providers = handler.get_active_providers()
        print(f"Active Providers: {[p.name for p in providers]}")

        # 0. Identify Current User
        print("\n--- Identifying Current User ---")
        try:
             # Just use the first provider
             provider = providers[0]
             p_inst = handler.create_provider_instance(provider)
             me = await p_inst.get_current_user()
             print(f"Current Token Owner: {me.name} (ID: {me.id})")
        except Exception as e:
             print(f"Error getting current user: {e}")
        
        # 2. Find target users (Phong, Steven Truong)
        print("\n--- Searching for Users ---")
        target_names = ["Phong", "Steven Truong", "Cao Phan", "Thai Do"]
        target_users = {}
        
        # Fetch all users first (streaming)
        all_users = await handler.list_users()
        print(f"Total Users Fetched: {len(all_users)}")
        
        for user in all_users:
            for name in target_names:
                if name.lower() in user['name'].lower():
                    target_users[user['id']] = user
                    print(f"Found User: {user['name']} (ID: {user['id']}, Provider: {user.get('provider_name')})")

        if not target_users:
            print("No target users found!")
            return

        # 3. Fetch Time Entries for Dec 22 - Dec 28
        start_date = "2024-12-22"
        end_date = "2024-12-28"
        
        print(f"\n--- Fetching Time Entries ({start_date} to {end_date}) ---")
        
        # Query for all target users at once
        user_ids = list(target_users.keys())
        print(f"Querying for User IDs: {user_ids}")
        
        try:
            entries = await handler.list_time_entries(
                user_id=user_ids,
                start_date=start_date,
                end_date=end_date
            )
            
            print(f"Total Entries Found: {len(entries)}")
            
            # Group by user
            entries_by_user = {}
            for entry in entries:
                uid = entry.get('user_id')
                if uid not in entries_by_user:
                    entries_by_user[uid] = []
                entries_by_user[uid].append(entry)
            
            for uid, user_entries in entries_by_user.items():
                user_name = target_users.get(uid, {}).get('name', 'Unknown')
                total_hours = sum(
                    float(e['hours'].replace('PT', '').replace('H', '')) 
                    if 'H' in e['hours'] else 0 
                    for e in user_entries
                )
                print(f"User: {user_name} (ID: {uid}) - Entries: {len(user_entries)}, Total Hours: {total_hours}")
                for e in user_entries:
                     print(f"  - {e['spentOn']}: {e['hours']} (Task: {e.get('task_id')})")
                     
            # Check users with NO entries
            for uid in user_ids:
                if uid not in entries_by_user:
                    user_name = target_users.get(uid, {}).get('name', 'Unknown')
                    print(f"User: {user_name} (ID: {uid}) - NO ENTRIES FOUND")

        except Exception as e:
            print(f"Error fetching time entries: {e}")
            import traceback
            traceback.print_exc()

        # 4. Fetch Time Entries for Project 480 (Test Project Context)
        print("\n--- Fetching Time Entries for Project 480 (No User Filter) ---")
        try:
             # Need to find the provider first to construct correct project ID if needed
             # But list_time_entries handles simple ID if provider_id is passed or implicitly handled?
             # Actually handler.list_time_entries iterates all providers.
             # If I pass project_id="480", it might fail validation if not composite.
             # But let's try passing provider_id too.
             
            provider = providers[0] # assuming single provider
            project_id = f"{provider.id}:480"
            
            entries = await handler.list_time_entries(
                project_id=project_id,
                # Try a wider range, e.g. last 3 months
                start_date="2024-10-01",
                end_date="2025-02-01"
            )
            print(f"Project 480 Entries Found: {len(entries)}")
            
            # Print unique user IDs found in this project's entries
            found_user_ids = set()
            for e in entries:
                uid = e.get('user_id')
                found_user_ids.add(uid)
                # Check if this entry belongs to our target users
                for target_uid in user_ids:
                    if uid and target_uid in uid: # strict or partial match
                         print(f"  -> FOUND ENTRY for target user {target_uid} in Project query! Entry: {e['id']}, Hours: {e['hours']}")

            print(f"Unique User IDs in Project 480 entries: {len(found_user_ids)}")
            if found_user_ids:
                print(f"First 5 User IDs: {list(found_user_ids)[:5]}")

        except Exception as e:
            print(f"Error fetching project time entries: {e}")
            traceback.print_exc()

    except Exception as e:
        print(f"Global Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(debug_missing_data())
