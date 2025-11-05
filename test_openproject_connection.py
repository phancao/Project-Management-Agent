#!/usr/bin/env python3
"""Test OpenProject connection"""
import os
import sys
from dotenv import load_dotenv
import requests
import base64

load_dotenv()

openproject_url = os.getenv('OPENPROJECT_URL', 'http://localhost:8080').rstrip('/')
openproject_key = os.getenv('OPENPROJECT_API_KEY', '')

if not openproject_key:
    print("❌ OPENPROJECT_API_KEY not found in .env")
    sys.exit(1)

print(f"Testing OpenProject connection to: {openproject_url}")
print(f"API Key: {openproject_key[:20]}...")

# Test connection
auth_string = f"apikey:{openproject_key}"
credentials = base64.b64encode(auth_string.encode()).decode()
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {credentials}"
}

try:
    # Test basic connectivity
    url = f"{openproject_url}/api/v3/projects"
    print(f"\nTesting URL: {url}")
    
    response = requests.get(url, headers=headers, timeout=10)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        projects = data.get("_embedded", {}).get("elements", [])
        print(f"✅ Success! Found {len(projects)} projects")
        if projects:
            print("\nFirst few projects:")
            for proj in projects[:3]:
                print(f"  - {proj.get('name')} (ID: {proj.get('id')})")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except requests.exceptions.ConnectionError as e:
    print(f"❌ Connection Error: {e}")
    print("Make sure OpenProject is running at http://localhost:8080")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
