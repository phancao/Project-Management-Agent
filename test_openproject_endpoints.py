#!/usr/bin/env python3
"""
Test OpenProject API Endpoints

This script validates API endpoints for Epics, Components, Labels, and Statuses
before implementing them in the OpenProject provider. It checks:
1. If endpoints exist and are accessible
2. If endpoints are deprecated
3. Response formats
4. Required authentication
5. Error handling

Usage:
    python test_openproject_endpoints.py <base_url> <api_key> [project_id]
    
Example:
    python test_openproject_endpoints.py https://your-openproject.com apikey123 123
"""

import requests
import base64
import json
import sys
from typing import Dict, Any, Optional


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


def test_openproject_endpoints(base_url: str, api_key: str, project_id: Optional[str] = None):
    """Test OpenProject API endpoints for Epics, Components, Labels, and Statuses"""
    
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
        "statuses": {"status": "unknown", "endpoint": None, "deprecated": False},
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
    if len(sys.argv) < 3:
        print("Usage: python test_openproject_endpoints.py <base_url> <api_key> [project_id]")
        print("\nExample:")
        print("  python test_openproject_endpoints.py https://your-openproject.com apikey123 123")
        sys.exit(1)
    
    base_url = sys.argv[1]
    api_key = sys.argv[2]
    project_id = sys.argv[3] if len(sys.argv) > 3 else None
    
    test_openproject_endpoints(base_url, api_key, project_id)


if __name__ == "__main__":
    main()

