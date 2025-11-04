#!/usr/bin/env python3
"""
Test script to verify JIRA SCRUM project access and implementation.

Usage:
    python3 test_jira_scrum_project.py [your-email@example.com]
"""
import sys
import base64
import requests
import json
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

jira_url = env_vars.get('JIRA_BASE_URL', 'https://phancao1984.atlassian.net').rstrip('/')
jira_token = env_vars.get('JIRA_API_TOKEN', '')
jira_email = env_vars.get('JIRA_EMAIL', '').split('#')[0].strip()

if len(sys.argv) > 1:
    jira_email = sys.argv[1]

if jira_email == 'your-email@example.com' or not jira_email:
    print("❌ Please provide your JIRA email")
    print(f"\nUsage: python3 {sys.argv[0]} <your-email@example.com>")
    print(f"\nOr set JIRA_EMAIL in .env file")
    sys.exit(1)

if not jira_token:
    print("❌ JIRA_API_TOKEN not found in .env")
    sys.exit(1)

print("="*70)
print("JIRA SCRUM Project Test")
print("="*70)
print(f"\nJIRA URL: {jira_url}")
print(f"Email: {jira_email}\n")

# Setup auth
auth_string = f"{jira_email}:{jira_token}"
auth_b64 = base64.b64encode(auth_string.encode()).decode()
headers = {
    "Authorization": f"Basic {auth_b64}",
    "Content-Type": "application/json"
}

try:
    # Test 1: Authentication
    print("1️⃣  Testing authentication...")
    response = requests.get(f"{jira_url}/rest/api/3/myself", headers=headers, timeout=10)
    if response.status_code == 200:
        user = response.json()
        print(f"   ✅ Authenticated as: {user.get('displayName')} ({user.get('emailAddress')})")
    else:
        print(f"   ❌ Auth failed: {response.status_code}")
        print(f"   {response.text[:200]}")
        sys.exit(1)
    
    # Test 2: List all projects
    print("\n2️⃣  Listing all projects...")
    response = requests.get(f"{jira_url}/rest/api/3/project", headers=headers, timeout=10)
    if response.status_code == 200:
        projects = response.json()
        print(f"   ✅ Found {len(projects)} project(s)\n")
        
        # Find SCRUM project
        scrum_project = None
        for proj in projects:
            if proj.get('key') == 'SCRUM':
                scrum_project = proj
                break
        
        if scrum_project:
            print(f"   🎯 SCRUM Project Found!")
            print(f"   Key: {scrum_project.get('key')}")
            print(f"   Name: {scrum_project.get('name')}")
            print(f"   Type: {scrum_project.get('projectTypeKey')}")
            print(f"   Style: {scrum_project.get('style', 'N/A')}")
            
            # Check if Next-Gen
            style = scrum_project.get('style', '')
            if 'next-gen' in str(style).lower():
                print(f"   📌 Type: Next-Gen Project (Space)")
            else:
                print(f"   📌 Type: Classic Project")
            
            print(f"\n   Full project data:")
            print(json.dumps(scrum_project, indent=2))
        else:
            print(f"   ⚠️  SCRUM project not found")
            print(f"\n   Available projects:")
            for proj in projects:
                print(f"     - {proj.get('key')}: {proj.get('name')}")
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"   {response.text[:300]}")
    
    # Test 3: Get SCRUM project directly
    print("\n3️⃣  Getting SCRUM project directly...")
    response = requests.get(f"{jira_url}/rest/api/3/project/SCRUM", headers=headers, timeout=10)
    if response.status_code == 200:
        project = response.json()
        print(f"   ✅ SCRUM project accessible")
        print(f"   Key: {project.get('key')}")
        print(f"   Name: {project.get('name')}")
    elif response.status_code == 404:
        print(f"   ❌ SCRUM project not found (404)")
    else:
        print(f"   ⚠️  Status: {response.status_code}")
    
    # Test 4: Get board for SCRUM
    print("\n4️⃣  Getting board for SCRUM project...")
    response = requests.get(
        f"{jira_url}/rest/agile/1.0/board",
        headers=headers,
        params={"projectKeyOrId": "SCRUM"},
        timeout=10
    )
    if response.status_code == 200:
        boards = response.json()
        board_list = boards.get('values', [])
        print(f"   ✅ Found {len(board_list)} board(s)")
        for board in board_list:
            print(f"      - {board.get('name')} (ID: {board.get('id')})")
            if board.get('id') == 1:
                print(f"        ✅ Matches board ID 1 from URL")
    else:
        print(f"   ⚠️  Could not get boards: {response.status_code}")
    
    # Test 5: Get issues from SCRUM
    print("\n5️⃣  Getting issues from SCRUM project...")
    response = requests.get(
        f"{jira_url}/rest/api/3/search",
        headers=headers,
        params={"jql": "project = SCRUM", "maxResults": 5},
        timeout=10
    )
    if response.status_code == 200:
        result = response.json()
        total = result.get('total', 0)
        issues = result.get('issues', [])
        print(f"   ✅ Found {total} total issue(s)")
        if issues:
            print(f"\n   Sample issues:")
            for issue in issues[:5]:
                print(f"      - {issue.get('key')}: {issue.get('fields', {}).get('summary', 'No summary')}")
        else:
            print(f"   ℹ️  No issues found (backlog might be empty)")
    
    print("\n" + "="*70)
    print("✅ All tests completed!")
    print("="*70)
    print("\nNext steps:")
    print("1. Update the provider with this email:")
    print(f"   python3 update_jira_provider.py {jira_email}")
    print("2. Verify the SCRUM project appears in provider management UI")
    print("3. Test backlog and sprint features")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
