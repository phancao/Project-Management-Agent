#!/usr/bin/env python3
"""
Test ClickUp API Endpoints

This script validates API endpoints for Epics, Labels, and Statuses
before implementing them in the ClickUp provider. It checks:
1. If endpoints exist and are accessible
2. If endpoints are deprecated
3. Response formats
4. Required authentication
5. Error handling

Usage:
    python test_clickup_endpoints.py <api_token> [space_id] [folder_id] [list_id]
    
Example:
    python test_clickup_endpoints.py pk_xxxxx 123456 789012 345678
"""

import requests
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


def test_clickup_endpoints(api_token: str, space_id: Optional[str] = None, 
                          folder_id: Optional[str] = None, list_id: Optional[str] = None):
    """Test ClickUp API endpoints for Epics, Labels, and Statuses"""
    
    print_header("Testing ClickUp API Endpoints")
    
    base_url = "https://api.clickup.com/api/v2"
    
    headers = {
        "Authorization": api_token,
        "Content-Type": "application/json"
    }
    
    results = {
        "epics": {"status": "unknown", "endpoint": None, "deprecated": False},
        "labels": {"status": "unknown", "endpoint": None, "deprecated": False},
        "statuses": {"status": "unknown", "endpoint": None, "deprecated": False},
    }
    
    # Test 1: Epics (ClickUp doesn't have explicit epics, but may use tasks or goals)
    print_header("1. Testing EPICS Endpoints")
    
    epic_endpoints = [
        {
            "name": "Get Tasks (may include epics)",
            "method": "GET",
            "url": f"{base_url}/list/{list_id}/task" if list_id else None,
            "params": {"archived": "false"}
        },
        {
            "name": "Get Goals (ClickUp's epic-like feature)",
            "method": "GET",
            "url": f"{base_url}/team/{space_id}/goal" if space_id else None
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
                print_success(f"Epics endpoint works!")
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
    
    # Test 2: Labels
    print_header("3. Testing LABELS Endpoints")
    
    label_endpoints = [
        {
            "name": "Get Labels",
            "method": "GET",
            "url": f"{base_url}/team/{space_id}/label" if space_id else None
        },
        {
            "name": "Get Task with Labels",
            "method": "GET",
            "url": f"{base_url}/task/{list_id}-1" if list_id else None,
            "note": "Requires existing task"
        }
    ]
    
    for endpoint in label_endpoints:
        if not endpoint.get('url'):
            continue
            
        try:
            print_info(f"Testing: {endpoint['name']}")
            print_info(f"URL: {endpoint['url']}")
            
            response = requests.get(endpoint['url'], headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"Labels endpoint works!")
                results["labels"]["status"] = "working"
                results["labels"]["endpoint"] = endpoint['url']
                break
            elif response.status_code == 410:
                print_error("Endpoint is deprecated (410 Gone)")
                results["labels"]["deprecated"] = True
            else:
                print_warning(f"Status: {response.status_code}")
                print_info(f"Response: {response.text[:200]}")
        except Exception as e:
            print_error(f"Error testing labels: {e}")
    
    # Test 3: Statuses
    print_header("4. Testing STATUSES Endpoints")
    
    status_endpoints = [
        {
            "name": "Get List Statuses",
            "method": "GET",
            "url": f"{base_url}/list/{list_id}" if list_id else None,
            "note": "Statuses are in list configuration"
        },
        {
            "name": "Get Space Statuses",
            "method": "GET",
            "url": f"{base_url}/space/{space_id}" if space_id else None
        }
    ]
    
    for endpoint in status_endpoints:
        if not endpoint.get('url'):
            continue
            
        try:
            print_info(f"Testing: {endpoint['name']}")
            print_info(f"URL: {endpoint['url']}")
            
            response = requests.get(endpoint['url'], headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"Statuses endpoint works!")
                # Try to extract statuses
                if 'statuses' in data:
                    statuses = data['statuses']
                    print_info(f"Found {len(statuses)} statuses")
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
    print_header("ClickUp API Test Summary")
    feature_names = {
        "epics": "EPICS",
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
        print("Usage: python test_clickup_endpoints.py <api_token> [space_id] [folder_id] [list_id]")
        print("\nExample:")
        print("  python test_clickup_endpoints.py pk_xxxxx 123456 789012 345678")
        print("\nNote: ClickUp uses API token for authentication")
        print("      Space ID, Folder ID, and List ID are optional but recommended for testing")
        sys.exit(1)
    
    api_token = sys.argv[1]
    space_id = sys.argv[2] if len(sys.argv) > 2 else None
    folder_id = sys.argv[3] if len(sys.argv) > 3 else None
    list_id = sys.argv[4] if len(sys.argv) > 4 else None
    
    test_clickup_endpoints(api_token, space_id, folder_id, list_id)


if __name__ == "__main__":
    main()

