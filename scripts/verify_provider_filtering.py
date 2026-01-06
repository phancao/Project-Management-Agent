
import requests
import json
import concurrent.futures
import time

PM_SERVICE_URL = "http://localhost:8001/api/v1"

def print_section(title):
    print(f"\n{'='*50}\n{title}\n{'='*50}")

def test_endpoint(url, description):
    print(f"\n--- {description} ---")
    print(f"URL: {url}")
    start_time = time.time()
    try:
        response = requests.get(url, timeout=60)
        duration = time.time() - start_time
        print(f"Status: {response.status_code}")
        print(f"Duration: {duration:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            total = data.get('total', 0)
            print(f"Items found: {len(items)} (Total: {total})")
            if items:
                print(f"First item sample: {json.dumps(items[0], indent=2)[:200]}...")
            return data
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

def verify_provider_filtering():
    print_section("VERIFYING PROVIDER-LEVEL ENDPOINTS")
    
    # 1. Get Providers
    print("\n>>> FETCHING PROVIDERS")
    providers_resp = test_endpoint(f"{PM_SERVICE_URL}/providers", "List Active Providers")
    if not providers_resp or not providers_resp.get('items'):
        print("No active providers found. Cannot proceed.")
        return

    providers = providers_resp['items']
    print(f"Found {len(providers)} providers: {[p['provider_type'] for p in providers]}")

    # 2. Test Global Users (No Filter)
    print_section("TEST 1: GLOBAL USERS (No Filter)")
    test_endpoint(f"{PM_SERVICE_URL}/users?limit=5", "Global Users")

    # 3. Test Provider-Specific Users
    print_section("TEST 2: PROVIDER-SPECIFIC USERS")
    for provider in providers:
        p_id = provider['id']
        p_type = provider['provider_type']
        test_endpoint(f"{PM_SERVICE_URL}/users?provider_id={p_id}&limit=5", f"Users for {p_type} ({p_id})")

    # 4. Test Provider-Specific Tasks (Just first provider)
    if providers:
        p_id = providers[0]['id']
        p_type = providers[0]['provider_type']
        print_section(f"TEST 3: PROVIDER-SPECIFIC TASKS ({p_type})")
        test_endpoint(f"{PM_SERVICE_URL}/tasks?provider_id={p_id}&limit=5", f"Tasks for {p_type}")

if __name__ == "__main__":
    verify_provider_filtering()
