#!/usr/bin/env python3
"""
Test script to check Sprint 4 tasks and their sprint_id extraction
"""
import requests
import base64
import json
import sys

# Configuration
BASE_URL = "https://openproject.bstarsolutions.com"
API_KEY = "79c2e8dda0e732dfacd653e99acf88a3ffe7111112ffd01ac331d076e4edf787"
PROJECT_ID = "478"  # AutoFlow QA
SPRINT_4_ID = "613"  # Sprint 4
TASK_IDS = ["85982", "85989", "85990", "87052"]  # Tasks that should be in Sprint 4

# Setup auth
auth_string = f"apikey:{API_KEY}"
credentials = base64.b64encode(auth_string.encode()).decode()
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {credentials}"
}

def get_task(task_id):
    """Fetch a single task with full details"""
    url = f"{BASE_URL}/api/v3/work_packages/{task_id}"
    params = {"include": "priority,status,assignee,project,version,parent"}
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def list_sprints(project_id):
    """List all sprints (versions) for a project"""
    url = f"{BASE_URL}/api/v3/versions"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    sprints = response.json()["_embedded"]["elements"]
    # Filter by project
    project_sprints = [
        s for s in sprints
        if s.get("_links", {}).get("definingProject", {}).get("href", "").endswith(f"/projects/{project_id}")
    ]
    return project_sprints

def extract_sprint_id(task_data):
    """Extract sprint_id using the same logic as the provider"""
    links = task_data.get("_links", {})
    embedded = task_data.get("_embedded", {})
    
    # First try _links.version.href
    version_href = links.get("version", {}).get("href")
    if version_href:
        return version_href.split("/")[-1]
    
    # Then try _embedded.version
    version_embedded = embedded.get("version")
    if version_embedded:
        if isinstance(version_embedded, dict):
            version_links = version_embedded.get("_links", {})
            if version_links.get("self", {}).get("href"):
                return version_links["self"]["href"].split("/")[-1]
            if version_embedded.get("id"):
                return str(version_embedded["id"])
    
    return None

print("=" * 80)
print("SPRINT 4 TASK INVESTIGATION")
print("=" * 80)

# First, list all sprints to find Sprint 4
print("\n1. Listing all sprints for project...")
sprints = list_sprints(PROJECT_ID)
print(f"Found {len(sprints)} sprints:")
for sprint in sprints:
    sprint_id = sprint.get("id")
    sprint_name = sprint.get("name", "Unknown")
    print(f"  - Sprint ID: {sprint_id}, Name: {sprint_name}")
    if "4" in sprint_name or sprint_id == SPRINT_4_ID:
        print(f"    *** This is Sprint 4! ID={sprint_id} ***")

# Now check each task
print(f"\n2. Checking tasks: {TASK_IDS}")
for task_id in TASK_IDS:
    print(f"\n--- Task {task_id} ---")
    try:
        task_data = get_task(task_id)
        
        # Show task info
        print(f"  Title: {task_data.get('subject', 'N/A')}")
        print(f"  Type: {task_data.get('_links', {}).get('type', {}).get('title', 'N/A')}")
        
        # Check version/sprint info
        links = task_data.get("_links", {})
        embedded = task_data.get("_embedded", {})
        
        print(f"  _links.version: {links.get('version')}")
        print(f"  _embedded.version: {embedded.get('version')}")
        
        # Extract sprint_id
        sprint_id = extract_sprint_id(task_data)
        print(f"  Extracted sprint_id: {sprint_id}")
        
        if sprint_id == SPRINT_4_ID:
            print(f"  ✅ MATCHES Sprint 4!")
        elif sprint_id:
            print(f"  ⚠️  Has sprint_id={sprint_id}, but expected {SPRINT_4_ID}")
        else:
            print(f"  ❌ NO sprint_id found!")
            
    except Exception as e:
        print(f"  ❌ Error fetching task: {e}")

print("\n" + "=" * 80)
print("Investigation complete")
print("=" * 80)

