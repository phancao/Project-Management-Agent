#!/usr/bin/env python3
"""Test OpenProject with new API key"""
import requests
import base64

openproject_url = "http://localhost:8080"
api_key = "69ee4607ab8f863e4e55b4a3a2fa9b6b95b35ecdd04747912ef5b921d38dbadb"

print(f"Testing OpenProject connection with new API key")
print(f"URL: {openproject_url}")

# Use apikey:API_KEY format (what the provider uses)
auth_string = f"apikey:{api_key}"
credentials = base64.b64encode(auth_string.encode()).decode()
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {credentials}"
}

try:
    response = requests.get(f"{openproject_url}/api/v3/projects", headers=headers, timeout=10)
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        projects = data.get("_embedded", {}).get("elements", [])
        print(f"✅ SUCCESS! Found {len(projects)} projects")
        if projects:
            print("\nProjects:")
            for proj in projects[:5]:
                print(f"  - {proj.get('name')} (ID: {proj.get('id')})")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
