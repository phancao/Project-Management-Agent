
import requests
import json
import time
import sys

# Configuration
PM_SERVICE_URL = "http://localhost:8001/api/v1"
TIMEOUT = 90  # Increased timeout for Global Tasks

def print_header(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")

def print_sub_header(title):
    print(f"\n--- {title} ---")

def test_endpoint(url, description, expect_error=False):
    print(f"Testing: {description}")
    print(f"URL: {url}")
    start_time = time.time()
    try:
        response = requests.get(url, timeout=TIMEOUT)
        duration = time.time() - start_time
        
        status_code = response.status_code
        print(f"Status: {status_code}")
        print(f"Duration: {duration:.2f}s")
        
        if status_code == 200:
            data = response.json()
            # Handle list response wrapper
            items = data.get('items', []) if isinstance(data, dict) else data
            total = data.get('total', len(items)) if isinstance(data, dict) else len(items)
            
            print(f"Items found: {len(items)} (Total reported: {total})")
            if items:
                # Print simplified sample of first item
                sample = items[0]
                simplified = {k: v for k, v in sample.items() if k in ['id', 'name', 'title', 'provider_id', 'provider_name']}
                print(f"Sample: {json.dumps(simplified)}")
            return True, data
        else:
            print(f"Response: {response.text[:200]}...")
            if expect_error:
                print("Error expected and received.")
                return True, None
            return False, None
            
    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT after {TIMEOUT}s")
        return False, None
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False, None

def run_suite():
    print_header("PM SERVICE ENDPOINT VERIFICATION SUITE")
    
    # 1. Providers
    print_sub_header("1. Providers Discovery")
    success, data = test_endpoint(f"{PM_SERVICE_URL}/providers", "List All Providers")
    if not success or not data:
        print("❌ CRITICAL: Cannot fetch providers. Aborting.")
        return

    providers = data.get('items', [])
    print(f"Active Providers: {len(providers)}")
    for p in providers:
        print(f" - {p.get('name')} (ID: {p.get('id')})")

    # 2. Users (Global & Provider)
    print_header("2. USERS ENDPOINTS")
    # Global
    print_sub_header("Global Users (Aggregated)")
    test_endpoint(f"{PM_SERVICE_URL}/users?limit=5", "Get Global Users")
    
    # Provider Specific
    if providers:
        p = providers[0]
        print_sub_header(f"Provider Users ({p.get('name')})")
        test_endpoint(f"{PM_SERVICE_URL}/users?provider_id={p['id']}&limit=5", f"Get Users for {p['name']}")

    # 3. Tasks (Global & Provider)
    print_header("3. TASKS ENDPOINTS")
    # Global - Note: This is heavy!
    print_sub_header("Global Tasks (Aggregated)")
    print("WARNING: This request gathers ALL tasks from ALL providers. It may be slow.")
    test_endpoint(f"{PM_SERVICE_URL}/tasks?limit=5", "Get Global Tasks", expect_error=False)
    
    # Provider Specific
    if providers:
        p = providers[0]
        print_sub_header(f"Provider Tasks ({p.get('name')})")
        test_endpoint(f"{PM_SERVICE_URL}/tasks?provider_id={p['id']}&limit=5", f"Get Tasks for {p['name']}")

    # 4. Time Entries (Global & Provider)
    print_header("4. TIME ENTRIES ENDPOINTS")
    # Global
    print_sub_header("Global Time Entries (Aggregated)")
    test_endpoint(f"{PM_SERVICE_URL}/time_entries?limit=5", "Get Global Time Entries")
    
    # Provider Specific
    if providers:
        p = providers[0]
        print_sub_header(f"Provider Time Entries ({p.get('name')})")
        test_endpoint(f"{PM_SERVICE_URL}/time_entries?provider_id={p['id']}&limit=5", f"Get Time Entries for {p['name']}")

    print_header("SUITE COMPLETE")

if __name__ == "__main__":
    run_suite()
