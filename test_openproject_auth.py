#!/usr/bin/env python3
"""Test different OpenProject authentication methods"""
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

print(f"Testing OpenProject authentication methods")
print(f"URL: {openproject_url}")
print(f"API Key: {openproject_key[:20]}...{openproject_key[-10:]}")
print()

# Method 1: apikey:API_KEY (current method)
print("Method 1: apikey:API_KEY")
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
    else:
        print(f"  ❌ Failed: {response.text[:200]}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print()

# Method 2: Just the API key as username, empty password
print("Method 2: API_KEY: (empty password)")
auth_string2 = f"{openproject_key}:"
credentials2 = base64.b64encode(auth_string2.encode()).decode()
headers2 = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {credentials2}"
}

try:
    response = requests.get(f"{openproject_url}/api/v3/projects", headers=headers2, timeout=10)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        print("  ✅ SUCCESS!")
    else:
        print(f"  ❌ Failed: {response.text[:200]}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print()

# Method 3: Check if API key format might be wrong
print("Checking API key format...")
print(f"  Length: {len(openproject_key)}")
print(f"  Contains spaces: {' ' in openproject_key}")
print(f"  Contains colons: {':' in openproject_key}")
print(f"  Starts with: {openproject_key[:10]}")
