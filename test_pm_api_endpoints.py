#!/usr/bin/env python3
"""
Test PM Provider API Endpoints

This script validates API endpoints for Epics, Components, Labels, and Workflows
before implementing them in the providers. It checks:
1. If endpoints exist and are accessible
2. If endpoints are deprecated
3. Response formats
4. Required authentication
5. Error handling

Usage:
    # Test JIRA
    python test_pm_api_endpoints.py jira <base_url> <email> <api_token> [project_key]
    
    # Test OpenProject
    python test_pm_api_endpoints.py openproject <base_url> <api_key> [project_id]
"""

import requests
import base64
import json
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")


def test_jira_endpoints(base_url: str, email: str, api_token: str, project_key: Optional[str] = None):
    """Test JIRA API endpoints for Epics, Components, Labels, and Workflows"""
    
    print_header("Testing JIRA API Endpoints")
    
    # Setup authentication
    auth_string = f"{email}:{api_token}"
    auth_b64 = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_b64}",
        "Accept": "application/json"
    }
    
    base_url = base_url.rstrip('/')
    
    results = {
        "epics": {"status": "unknown", "endpoint": None, "deprecated": False},
        "components": {"status": "unknown", "endpoint": None, "deprecated": False},
        "labels": {"status": "unknown", "endpoint": None, "deprecated": False},
        "workflows": {"status": "unknown", "endpoint": None, "deprecated": False},
    }
    
    # Test 1: Epics
    print_header("1. Testing EPICS Endpoints")
    
    epic_endpoints = [
        {
            "name": "Search Epics (issuetype=Epic)",
            "method": "POST",
            "url": f"{base_url}/rest/api/3/search/jql",
            "body": {
                "jql": f'project = "{project_key}" AND issuetype = Epic' if project_key else 'issuetype = Epic',
                "maxResults": 5,
                "fields": ["summary", "status", "description", "project"]
            }
        },
        {
            "name": "Search Epics (alternative)",
            "method": "GET",
            "url": f"{base_url}/rest/api/3/search",
            "params": {
                "jql": f'project = "{project_key}" AND issuetype = Epic' if project_key else 'issuetype = Epic',
                "maxResults": 5
            }
        }
    ]
    
    for endpoint in epic_endpoints:
        try:
            print_info(f"Testing: {endpoint['name']}")
            print_info(f"URL: {endpoint['url']}")
            
            if endpoint['method'] == 'POST':
                response = requests.post(
                    endpoint['url'],
                    headers=headers,
                    json=endpoint.get('body', {}),
                    timeout=10
                )
            else:
                response = requests.get(
                    endpoint['url'],
                    headers=headers,
                    params=endpoint.get('params', {}),
                    timeout=10
                )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                epics_count = len(data.get('issues', []))
                print_success(f"Epics endpoint works! Found {epics_count} epics")
                results["epics"]["status"] = "working"
                results["epics"]["endpoint"] = endpoint['url']
                results["epics"]["method"] = endpoint['method']
                break
            elif response.status_code == 410:
                print_error("Endpoint is deprecated (410 Gone)")
                results["epics"]["deprecated"] = True
                error_data = response.json() if response.text else {}
                print_error(f"Error: {error_data.get('errorMessages', ['Unknown error'])}")
            elif response.status_code == 400:
                print_warning("Bad request - may need different JQL or project")
                print_info(f"Response: {response.text[:200]}")
            else:
                print_warning(f"Unexpected status: {response.status_code}")
                print_info(f"Response: {response.text[:200]}")
        except Exception as e:
            print_error(f"Error testing epics: {e}")
    
    # Test 2: Components
    print_header("2. Testing COMPONENTS Endpoints")
    
    if project_key:
        component_endpoints = [
            {
                "name": "Get Project Components",
                "method": "GET",
                "url": f"{base_url}/rest/api/3/project/{project_key}/components"
            },
            {
                "name": "List All Components",
                "method": "GET",
                "url": f"{base_url}/rest/api/3/project/{project_key}/components"
            }
        ]
        
        for endpoint in component_endpoints:
            try:
                print_info(f"Testing: {endpoint['name']}")
                print_info(f"URL: {endpoint['url']}")
                
                response = requests.get(endpoint['url'], headers=headers, timeout=10)
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    components = response.json()
                    print_success(f"Components endpoint works! Found {len(components)} components")
                    if components:
                        print_info(f"Sample component: {components[0].get('name', 'N/A')}")
                    results["components"]["status"] = "working"
                    results["components"]["endpoint"] = endpoint['url']
                    break
                elif response.status_code == 410:
                    print_error("Endpoint is deprecated (410 Gone)")
                    results["components"]["deprecated"] = True
                elif response.status_code == 404:
                    print_warning("Project not found or no components")
                else:
                    print_warning(f"Status: {response.status_code}")
                    print_info(f"Response: {response.text[:200]}")
            except Exception as e:
                print_error(f"Error testing components: {e}")
    else:
        print_warning("Project key not provided, skipping component test")
    
    # Test 3: Labels
    print_header("3. Testing LABELS Endpoints")
    
    label_endpoints = [
        {
            "name": "Search with Labels",
            "method": "POST",
            "url": f"{base_url}/rest/api/3/search/jql",
            "body": {
                "jql": f'project = "{project_key}" AND labels IS NOT EMPTY' if project_key else 'labels IS NOT EMPTY',
                "maxResults": 5,
                "fields": ["summary", "labels"]
            }
        },
        {
            "name": "Get Labels from Issue",
            "method": "GET",
            "url": f"{base_url}/rest/api/3/issue/{project_key}-1" if project_key else None,
            "note": "Requires existing issue"
        }
    ]
    
    for endpoint in label_endpoints:
        if not endpoint.get('url'):
            continue
            
        try:
            print_info(f"Testing: {endpoint['name']}")
            print_info(f"URL: {endpoint['url']}")
            
            if endpoint['method'] == 'POST':
                response = requests.post(
                    endpoint['url'],
                    headers=headers,
                    json=endpoint.get('body', {}),
                    timeout=10
                )
            else:
                response = requests.get(endpoint['url'], headers=headers, timeout=10)
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                if endpoint['method'] == 'POST':
                    data = response.json()
                    issues = data.get('issues', [])
                    if issues:
                        labels = issues[0].get('fields', {}).get('labels', [])
                        print_success(f"Labels endpoint works! Found labels: {labels}")
                        results["labels"]["status"] = "working"
                        results["labels"]["endpoint"] = endpoint['url']
                        break
                else:
                    data = response.json()
                    labels = data.get('fields', {}).get('labels', [])
                    print_success(f"Labels endpoint works! Found labels: {labels}")
                    results["labels"]["status"] = "working"
                    results["labels"]["endpoint"] = endpoint['url']
                    break
            elif response.status_code == 410:
                print_error("Endpoint is deprecated (410 Gone)")
                results["labels"]["deprecated"] = True
            elif response.status_code == 404:
                print_warning("Issue not found (expected if issue doesn't exist)")
            else:
                print_warning(f"Status: {response.status_code}")
                print_info(f"Response: {response.text[:200]}")
        except Exception as e:
            print_error(f"Error testing labels: {e}")
    
    # Test 4: Statuses (for UI columns)
    print_header("4. Testing STATUSES Endpoints")
    
    status_endpoints = [
        {
            "name": "Get All Statuses",
            "method": "GET",
            "url": f"{base_url}/rest/api/3/status"
        },
        {
            "name": "Get Statuses for Project",
            "method": "GET",
            "url": f"{base_url}/rest/api/3/project/{project_key}/statuses" if project_key else None
        },
        {
            "name": "Get Issue Type Statuses",
            "method": "GET",
            "url": f"{base_url}/rest/api/3/project/{project_key}/statuses" if project_key else None,
            "params": {"expand": "statuses"} if project_key else {}
        }
    ]
    
    for endpoint in status_endpoints:
        if not endpoint.get('url'):
            continue
            
        try:
            print_info(f"Testing: {endpoint['name']}")
            print_info(f"URL: {endpoint['url']}")
            
            if endpoint['method'] == 'GET':
                response = requests.get(
                    endpoint['url'],
                    headers=headers,
                    params=endpoint.get('params', {}),
                    timeout=10
                )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"Statuses endpoint works!")
                # Try to extract status names
                if isinstance(data, list):
                    status_names = [s.get('name', s.get('id', '')) for s in data[:5]]
                    print_info(f"Sample statuses: {status_names}")
                elif isinstance(data, dict):
                    print_info(f"Response structure: {list(data.keys())[:5]}")
                results["workflows"]["status"] = "working"
                results["workflows"]["endpoint"] = endpoint['url']
                break
            elif response.status_code == 410:
                print_error("Endpoint is deprecated (410 Gone)")
                results["workflows"]["deprecated"] = True
                error_data = response.json() if response.text else {}
                print_error(f"Error: {error_data.get('errorMessages', ['Unknown error'])}")
            elif response.status_code == 404:
                print_warning("Not found (may need existing project)")
            else:
                print_warning(f"Status: {response.status_code}")
                print_info(f"Response: {response.text[:200]}")
        except Exception as e:
            print_error(f"Error testing statuses: {e}")
    
    # Summary
    print_header("JIRA API Test Summary")
    feature_names = {
        "epics": "EPICS",
        "components": "COMPONENTS",
        "labels": "LABELS",
        "statuses": "STATUSES"
    }
    for feature, result in results.items():
        status = result['status']
        feature_display = feature_names.get(feature, feature.upper())
        if status == "working":
            print_success(f"{feature_display}: ✅ Working - {result.get('endpoint', 'N/A')}")
        elif result.get('deprecated'):
            print_error(f"{feature_display}: ❌ Deprecated")
        else:
            print_warning(f"{feature_display}: ⚠️  Not tested or failed")
    
    return results


def test_openproject_endpoints(base_url: str, api_key: str, project_id: Optional[str] = None):
    """Test OpenProject API endpoints for Epics, Components, Labels, and Workflows"""
    
    print_header("Testing OpenProject API Endpoints")
    
    # Setup authentication
    auth_string = f"apikey:{api_key}"
    credentials = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {credentials}"
    }
    
    base_url = base_url.rstrip('/')
    
    results = {
        "epics": {"status": "unknown", "endpoint": None, "deprecated": False},
        "components": {"status": "unknown", "endpoint": None, "deprecated": False},
        "labels": {"status": "unknown", "endpoint": None, "deprecated": False},
        "workflows": {"status": "unknown", "endpoint": None, "deprecated": False},
    }
    
    # Test 1: Epics (Work Packages with type Epic)
    print_header("1. Testing EPICS Endpoints")
    
    epic_endpoints = [
        {
            "name": "List Work Packages (type filter)",
            "method": "GET",
            "url": f"{base_url}/api/v3/work_packages",
            "params": {
                "filters": json.dumps([{
                    "type": {"operator": "=", "values": ["Epic"]}
                }]),
                "pageSize": 5
            }
        },
        {
            "name": "List Work Packages by Project (type filter)",
            "method": "GET",
            "url": f"{base_url}/api/v3/projects/{project_id}/work_packages" if project_id else None,
            "params": {
                "filters": json.dumps([{
                    "type": {"operator": "=", "values": ["Epic"]}
                }]),
                "pageSize": 5
            }
        }
    ]
    
    for endpoint in epic_endpoints:
        if not endpoint.get('url'):
            continue
            
        try:
            print_info(f"Testing: {endpoint['name']}")
            print_info(f"URL: {endpoint['url']}")
            
            response = requests.get(
                endpoint['url'],
                headers=headers,
                params=endpoint.get('params', {}),
                timeout=10
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                work_packages = data.get('_embedded', {}).get('elements', [])
                epics = [wp for wp in work_packages if wp.get('_links', {}).get('type', {}).get('title') == 'Epic']
                print_success(f"Epics endpoint works! Found {len(epics)} epics")
                results["epics"]["status"] = "working"
                results["epics"]["endpoint"] = endpoint['url']
                break
            elif response.status_code == 410:
                print_error("Endpoint is deprecated (410 Gone)")
                results["epics"]["deprecated"] = True
            else:
                print_warning(f"Status: {response.status_code}")
                print_info(f"Response: {response.text[:200]}")
        except Exception as e:
            print_error(f"Error testing epics: {e}")
    
    # Test 2: Components (Categories or Custom Fields)
    print_header("2. Testing COMPONENTS Endpoints")
    
    component_endpoints = [
        {
            "name": "Get Project Categories",
            "method": "GET",
            "url": f"{base_url}/api/v3/projects/{project_id}/categories" if project_id else None
        },
        {
            "name": "List All Categories",
            "method": "GET",
            "url": f"{base_url}/api/v3/categories"
        }
    ]
    
    for endpoint in component_endpoints:
        if not endpoint.get('url'):
            continue
            
        try:
            print_info(f"Testing: {endpoint['name']}")
            print_info(f"URL: {endpoint['url']}")
            
            response = requests.get(endpoint['url'], headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                categories = data.get('_embedded', {}).get('elements', [])
                print_success(f"Components/Categories endpoint works! Found {len(categories)} categories")
                if categories:
                    print_info(f"Sample category: {categories[0].get('name', 'N/A')}")
                results["components"]["status"] = "working"
                results["components"]["endpoint"] = endpoint['url']
                break
            elif response.status_code == 410:
                print_error("Endpoint is deprecated (410 Gone)")
                results["components"]["deprecated"] = True
            else:
                print_warning(f"Status: {response.status_code}")
                print_info(f"Response: {response.text[:200]}")
        except Exception as e:
            print_error(f"Error testing components: {e}")
    
    # Test 3: Labels (Categories or Custom Fields)
    print_header("3. Testing LABELS Endpoints")
    
    label_endpoints = [
        {
            "name": "Get Work Package with Categories",
            "method": "GET",
            "url": f"{base_url}/api/v3/work_packages",
            "params": {"pageSize": 1},
            "note": "Labels may be in categories field"
        }
    ]
    
    for endpoint in label_endpoints:
        try:
            print_info(f"Testing: {endpoint['name']}")
            print_info(f"URL: {endpoint['url']}")
            
            response = requests.get(
                endpoint['url'],
                headers=headers,
                params=endpoint.get('params', {}),
                timeout=10
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                work_packages = data.get('_embedded', {}).get('elements', [])
                if work_packages:
                    wp = work_packages[0]
                    categories = wp.get('_links', {}).get('categories', [])
                    print_success(f"Labels/Categories endpoint works! Found categories in work packages")
                    results["labels"]["status"] = "working"
                    results["labels"]["endpoint"] = endpoint['url']
                    break
            elif response.status_code == 410:
                print_error("Endpoint is deprecated (410 Gone)")
                results["labels"]["deprecated"] = True
            else:
                print_warning(f"Status: {response.status_code}")
        except Exception as e:
            print_error(f"Error testing labels: {e}")
    
    # Test 4: Statuses
    print_header("4. Testing STATUSES Endpoints")
    
    status_endpoints = [
        {
            "name": "Get Statuses",
            "method": "GET",
            "url": f"{base_url}/api/v3/statuses"
        },
        {
            "name": "Get Work Package Types",
            "method": "GET",
            "url": f"{base_url}/api/v3/types"
        }
    ]
    
    for endpoint in status_endpoints:
        try:
            print_info(f"Testing: {endpoint['name']}")
            print_info(f"URL: {endpoint['url']}")
            
            response = requests.get(endpoint['url'], headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                elements = data.get('_embedded', {}).get('elements', [])
                print_success(f"Statuses endpoint works! Found {len(elements)} statuses/types")
                if elements:
                    print_info(f"Sample status: {elements[0].get('name', 'N/A')}")
                results["statuses"]["status"] = "working"
                results["statuses"]["endpoint"] = endpoint['url']
                break
            elif response.status_code == 410:
                print_error("Endpoint is deprecated (410 Gone)")
                results["statuses"]["deprecated"] = True
            else:
                print_warning(f"Status: {response.status_code}")
                print_info(f"Response: {response.text[:200]}")
        except Exception as e:
            print_error(f"Error testing statuses: {e}")
    
    # Summary
    print_header("OpenProject API Test Summary")
    feature_names = {
        "epics": "EPICS",
        "components": "COMPONENTS",
        "labels": "LABELS",
        "statuses": "STATUSES"
    }
    for feature, result in results.items():
        status = result['status']
        feature_display = feature_names.get(feature, feature.upper())
        if status == "working":
            print_success(f"{feature_display}: ✅ Working - {result.get('endpoint', 'N/A')}")
        elif result.get('deprecated'):
            print_error(f"{feature_display}: ❌ Deprecated")
        else:
            print_warning(f"{feature_display}: ⚠️  Not tested or failed")
    
    return results


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  JIRA:    python test_pm_api_endpoints.py jira <base_url> <email> <api_token> [project_key]")
        print("  OpenProject: python test_pm_api_endpoints.py openproject <base_url> <api_key> [project_id]")
        print("\nExample:")
        print("  python test_pm_api_endpoints.py jira https://your-domain.atlassian.net email@example.com token SCRUM")
        print("  python test_pm_api_endpoints.py openproject https://your-openproject.com apikey123 123")
        sys.exit(1)
    
    provider = sys.argv[1].lower()
    
    if provider == "jira":
        if len(sys.argv) < 5:
            print("Error: JIRA requires base_url, email, api_token, and optional project_key")
            sys.exit(1)
        base_url = sys.argv[2]
        email = sys.argv[3]
        api_token = sys.argv[4]
        project_key = sys.argv[5] if len(sys.argv) > 5 else None
        test_jira_endpoints(base_url, email, api_token, project_key)
    
    elif provider == "openproject":
        if len(sys.argv) < 4:
            print("Error: OpenProject requires base_url, api_key, and optional project_id")
            sys.exit(1)
        base_url = sys.argv[2]
        api_key = sys.argv[3]
        project_id = sys.argv[4] if len(sys.argv) > 4 else None
        test_openproject_endpoints(base_url, api_key, project_id)
    
    else:
        print(f"Error: Unknown provider '{provider}'. Use 'jira' or 'openproject'")
        sys.exit(1)


if __name__ == "__main__":
    main()

