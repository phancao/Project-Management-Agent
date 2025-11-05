#!/usr/bin/env python3
"""Test OpenProject with username"""
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

print(f"Testing OpenProject with different authentication methods")
print(f"URL: {openproject_url}")
print()

# Method 1: apikey:API_KEY (current - what the provider uses)
print("Method 1: apikey:API_KEY (current provider method)")
auth_string = f"apikey:{openproject_key}"
credentials = base64.b64encode(auth_string.encode()).decode()
headers1 = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {credentials}"
}

try:
    response = requests.get(f"{openproject_url}/api/v3/projects", headers=headers1, timeout=10)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        print("  ✅ SUCCESS!")
        data = response.json()
        projects = data.get("_embedded", {}).get("elements", [])
        print(f"  Found {len(projects)} projects")
    else:
        print(f"  ❌ Failed: {response.text[:200]}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print()

# Method 2: username:API_KEY (if username is required)
print("Method 2: Trying common usernames")
for username in ["admin", "apikey", "openproject"]:
    auth_string = f"{username}:{openproject_key}"
    credentials = base64.b64encode(auth_string.encode()).decode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {credentials}"
    }
    try:
        response = requests.get(f"{openproject_url}/api/v3/projects", headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"  ✅ SUCCESS with username '{username}'!")
            data = response.json()
            projects = data.get("_embedded", {}).get("elements", [])
            print(f"  Found {len(projects)} projects")
            break
        else:
            print(f"  ❌ Failed with '{username}': {response.status_code}")
    except Exception as e:
        print(f"  ❌ Error with '{username}': {e}")

print()
print("Note: If all methods fail, the API key might be invalid or expired.")
print("Please check:")
print("  1. Generate a new API key in OpenProject (My Account → Access Token)")
print("  2. Make sure the API key is correct in .env")
print("  3. Verify OpenProject is running and accessible")
