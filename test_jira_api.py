#!/usr/bin/env python3
"""
Test script to directly test JIRA API queries
This helps debug issues without going through the full application stack
"""
import requests
import base64
import json
import sys
from typing import Optional

def test_jira_search(
    base_url: str,
    email: str,
    api_token: str,
    project_key: str
):
    """Test JIRA search API directly"""
    
    # Setup authentication
    auth_string = f"{email}:{api_token}"
    auth_bytes = auth_string.encode('utf-8')
    auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_b64}",
        "Accept": "application/json"
    }
    
    # Test 1: Get project info
    print("=" * 80)
    print("TEST 1: Get Project Info")
    print("=" * 80)
    project_url = f"{base_url}/rest/api/3/project/{project_key}"
    print(f"URL: {project_url}")
    print(f"Headers: {dict(headers)}")
    
    try:
        response = requests.get(project_url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text[:1000]}")
        
        if response.status_code == 200:
            project_data = response.json()
            print(f"Project Key: {project_data.get('key')}")
            print(f"Project ID: {project_data.get('id')}")
            print(f"Project Name: {project_data.get('name')}")
            print(f"Project Type: {project_data.get('projectTypeKey')}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()
    
    # Test 2: Search with quoted project key
    print("=" * 80)
    print("TEST 2: Search with Quoted Project Key")
    print("=" * 80)
    search_url = f"{base_url}/rest/api/3/search"
    jql = f'project = "{project_key}"'
    params = {
        "jql": jql,
        "maxResults": 10,
        "fields": ["summary", "status", "project"]
    }
    
    print(f"URL: {search_url}")
    print(f"JQL: {jql}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(
            search_url, headers=headers, params=params, timeout=30
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text (first 2000 chars): {response.text[:2000]}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Total Issues: {data.get('total', 0)}")
            print(f"Issues Returned: {len(data.get('issues', []))}")
            if data.get('issues'):
                print(f"First Issue Key: {data['issues'][0].get('key')}")
        elif response.status_code == 410:
            try:
                error_data = response.json()
                print(f"Error Messages: {error_data.get('errorMessages', [])}")
                print(f"Errors: {error_data.get('errors', {})}")
            except:
                pass
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()
    
    # Test 3: Search with unquoted project key
    print("=" * 80)
    print("TEST 3: Search with Unquoted Project Key")
    print("=" * 80)
    jql2 = f"project = {project_key}"
    params2 = {
        "jql": jql2,
        "maxResults": 10,
        "fields": ["summary", "status", "project"]
    }
    
    print(f"JQL: {jql2}")
    print(f"Params: {params2}")
    
    try:
        response = requests.get(
            search_url, headers=headers, params=params2, timeout=30
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response Text (first 2000 chars): {response.text[:2000]}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()
    
    # Test 4: Search all issues (no project filter)
    print("=" * 80)
    print("TEST 4: Search All Issues (No Project Filter)")
    print("=" * 80)
    jql3 = "ORDER BY created DESC"
    params3 = {
        "jql": jql3,
        "maxResults": 10,
        "fields": ["summary", "status", "project"]
    }
    
    print(f"JQL: {jql3}")
    
    try:
        response = requests.get(
            search_url, headers=headers, params=params3, timeout=30
        )
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total Issues: {data.get('total', 0)}")
            issues = data.get('issues', [])
            print(f"Issues Returned: {len(issues)}")
            # Check if our project appears in results
            project_issues = [
                issue for issue in issues
                if issue.get('fields', {}).get('project', {}).get('key') == project_key
            ]
            print(f"Issues from project {project_key}: {len(project_issues)}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python test_jira_api.py <base_url> <email> <api_token> <project_key>")
        print("Example: python test_jira_api.py https://your-domain.atlassian.net your@email.com your_token SCRUM")
        sys.exit(1)
    
    base_url = sys.argv[1].rstrip('/')
    email = sys.argv[2]
    api_token = sys.argv[3]
    project_key = sys.argv[4]
    
    test_jira_search(base_url, email, api_token, project_key)

