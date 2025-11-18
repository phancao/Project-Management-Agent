#!/usr/bin/env python3
"""
Helper script to update JIRA provider with correct email
"""
import requests
import sys
from pathlib import Path

# Load .env
env_path = Path('.env')
env_vars = {}
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                parts = line.strip().split('=', 1)
                if len(parts) == 2:
                    key, value = parts
                    env_vars[key] = value.strip()

jira_url = env_vars.get('JIRA_BASE_URL', '')
jira_token = env_vars.get('JIRA_API_TOKEN', '')
jira_email = env_vars.get('JIRA_EMAIL', '').split('#')[0].strip()

# Provider ID from earlier test
provider_id = "2afd16cd-2a29-421d-851e-9b8ae963a67f"

if len(sys.argv) > 1:
    jira_email = sys.argv[1]

if jira_email == 'your-email@example.com' or not jira_email:
    print("❌ Please provide your JIRA email address")
    print(f"\nUsage: python3 {sys.argv[0]} <your-email@example.com>")
    print(f"\nOr update JIRA_EMAIL in .env file")
    sys.exit(1)

print(f"Updating JIRA provider with email: {jira_email}")

request_data = {
    'provider_type': 'jira',
    'base_url': jira_url,
    'api_token': jira_token,
    'email': jira_email
}

try:
    response = requests.put(
        f'http://localhost:8000/api/pm/providers/{provider_id}',
        json=request_data,
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Provider updated successfully!")
        print(f"   Provider ID: {result.get('id')}")
        
        # Test connection
        print("\n🔍 Testing connection...")
        projects_response = requests.get(
            f'http://localhost:8000/api/pm/providers/{provider_id}/projects',
            timeout=30
        )
        
        if projects_response.status_code == 200:
            projects_data = projects_response.json()
            print(f"✅ Connection successful!")
            print(f"   Found {projects_data.get('total_projects', 0)} projects")
            if projects_data.get('projects'):
                print("\n📋 Projects:")
                for proj in projects_data['projects'][:10]:
                    print(f"   - {proj.get('name')} ({proj.get('id')})")
        else:
            print(f"⚠️  Could not fetch projects: {projects_response.status_code}")
            print(f"   {projects_response.text[:200]}")
    else:
        print(f"❌ Failed to update provider: {response.status_code}")
        print(f"   {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")
