#!/usr/bin/env python3
"""Quick script to check API key and list projects"""
import os
import sys
from dotenv import load_dotenv
import requests

load_dotenv()
api_key = os.getenv('OPENPROJECT_API_KEY')
base_url = os.getenv('OPENPROJECT_URL', 'http://localhost:8080')

if not api_key:
    print("❌ OPENPROJECT_API_KEY not set in .env")
    sys.exit(1)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {api_key}"
}

# Test connection
try:
    response = requests.get(f"{base_url}/api/v3/projects", headers=headers, timeout=5)
    if response.status_code == 200:
        print("✅ API key is valid!")
        projects = response.json().get("_embedded", {}).get("elements", [])
        print(f"✅ Found {len(projects)} project(s)")
        for p in projects[:3]:
            print(f"   - {p.get('name')} (ID: {p.get('id')})")
    else:
        print(f"❌ API key test failed: HTTP {response.status_code}")
        print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"❌ Error: {e}")
