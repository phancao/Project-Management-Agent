#!/usr/bin/env python3
"""Test script to debug OpenProject status update issue"""
import requests
import base64
import json
import sys

# Configuration - adjust these to match your setup
BASE_URL = "http://localhost:8080"
API_KEY = "your-api-key-here"  # Replace with actual API key
TASK_ID = "14"
STATUS_ID = "4"

# Setup auth
auth_string = f"apikey:{API_KEY}"
credentials = base64.b64encode(auth_string.encode()).decode()
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {credentials}"
}

print(f"Testing OpenProject status update for task {TASK_ID} to status {STATUS_ID}")
print("=" * 80)

# Step 1: Get current task to see its current status
print("\n1. Getting current task...")
task_url = f"{BASE_URL}/api/v3/work_packages/{TASK_ID}"
response = requests.get(task_url, headers=headers)
if response.status_code == 200:
    task_data = response.json()
    current_status = task_data.get("_links", {}).get("status", {}).get("title", "Unknown")
    lock_version = task_data.get("lockVersion")
    print(f"   Current status: {current_status}")
    print(f"   Lock version: {lock_version}")
else:
    print(f"   ERROR: Failed to get task: {response.status_code}")
    print(f"   Response: {response.text}")
    sys.exit(1)

# Step 2: Get available statuses
print("\n2. Getting available statuses...")
statuses_url = f"{BASE_URL}/api/v3/statuses"
response = requests.get(statuses_url, headers=headers)
if response.status_code == 200:
    statuses = response.json().get("_embedded", {}).get("elements", [])
    print(f"   Found {len(statuses)} statuses:")
    for status in statuses:
        status_id = status.get("id")
        status_name = status.get("name")
        is_default = status.get("isDefault", False)
        marker = " (default)" if is_default else ""
        print(f"     ID {status_id}: {status_name}{marker}")
    
    # Check if status ID 4 exists
    status_4 = next((s for s in statuses if s.get("id") == 4), None)
    if status_4:
        print(f"\n   ✓ Status ID 4 exists: {status_4.get('name')}")
    else:
        print(f"\n   ✗ Status ID 4 NOT FOUND in available statuses!")
        print(f"   Available IDs: {[s.get('id') for s in statuses]}")
else:
    print(f"   ERROR: Failed to get statuses: {response.status_code}")
    print(f"   Response: {response.text}")

# Step 3: Test form endpoint with status update
print("\n3. Testing form endpoint with status update...")
form_url = f"{BASE_URL}/api/v3/work_packages/{TASK_ID}/form"
payload = {
    "_links": {
        "status": {
            "href": f"/api/v3/statuses/{STATUS_ID}"
        }
    }
}
print(f"   Payload: {json.dumps(payload, indent=2)}")
response = requests.post(form_url, headers=headers, json=payload)
print(f"   Status code: {response.status_code}")

if response.status_code == 200:
    form_data = response.json()
    validated_payload = form_data.get("_embedded", {}).get("payload", {})
    print(f"   ✓ Form validation successful")
    print(f"   Validated payload: {json.dumps(validated_payload, indent=2)}")
    
    # Step 4: Try the actual update
    print("\n4. Attempting actual update...")
    update_url = f"{BASE_URL}/api/v3/work_packages/{TASK_ID}"
    update_response = requests.patch(update_url, headers=headers, json=validated_payload)
    print(f"   Status code: {update_response.status_code}")
    
    if update_response.status_code == 200:
        print(f"   ✓ Update successful!")
        updated_task = update_response.json()
        new_status = updated_task.get("_links", {}).get("status", {}).get("title", "Unknown")
        print(f"   New status: {new_status}")
    else:
        print(f"   ✗ Update failed")
        print(f"   Response: {update_response.text}")
        try:
            error_data = update_response.json()
            print(f"   Error JSON: {json.dumps(error_data, indent=2)}")
        except:
            pass
else:
    print(f"   ✗ Form validation failed")
    print(f"   Response: {response.text}")
    try:
        error_data = response.json()
        print(f"   Error JSON: {json.dumps(error_data, indent=2)}")
        
        # Extract detailed errors
        if "_embedded" in error_data and "errors" in error_data["_embedded"]:
            errors = error_data["_embedded"]["errors"]
            print(f"\n   Detailed errors:")
            for err in errors:
                msg = err.get("message", "")
                attr = err.get("_attribute", "")
                print(f"     - {attr}: {msg}")
    except:
        pass

print("\n" + "=" * 80)



