#!/usr/bin/env python3
"""
Analyze differences between OpenProject v13 and v16 APIs.

This script tests key API endpoints used by import_work_packages.py
to identify version-specific differences.
"""

import json
import sys
from typing import Dict, List, Optional

import requests


def test_endpoint(
    base_url: str,
    token: str,
    method: str,
    path: str,
    data: Optional[dict] = None,
) -> Dict:
    """Test an API endpoint and return response info."""
    url = f"{base_url.rstrip('/')}/api/v3{path}"
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        return {
            "status": resp.status_code,
            "has_data": bool(resp.text),
            "content_type": resp.headers.get("Content-Type", ""),
            "sample": resp.text[:200] if resp.text else "",
        }
    except Exception as e:
        return {"error": str(e)}


def analyze_version(base_url: str, token: str, version_name: str) -> Dict:
    """Analyze API endpoints for a specific version."""
    print(f"\n{'='*60}")
    print(f"Analyzing {version_name}")
    print(f"{'='*60}\n")
    
    results = {}
    
    # Test endpoints used in import_work_packages.py
    endpoints = [
        # Collection endpoints
        ("GET", "/users", "List users"),
        ("GET", "/projects", "List projects"),
        ("GET", "/types", "List types"),
        ("GET", "/roles", "List roles"),
        ("GET", "/time_entries", "List time entries"),
        ("GET", "/time_entries/activities", "List time entry activities"),
        
        # Single resource endpoints (will fail without IDs, but we check structure)
        ("GET", "/status", "API status"),
    ]
    
    for method, path, description in endpoints:
        print(f"Testing {description} ({method} {path})...")
        result = test_endpoint(base_url, token, method, path)
        results[path] = result
        
        if "error" in result:
            print(f"  ❌ Error: {result['error']}")
        elif result.get("status") == 200:
            print(f"  ✅ Status: {result['status']}")
        elif result.get("status") == 401:
            print(f"  ⚠️  Unauthenticated (expected if no token)")
        elif result.get("status") == 404:
            print(f"  ❌ Not found (endpoint may not exist)")
        else:
            print(f"  ⚠️  Status: {result['status']}")
    
    return results


def compare_results(v13_results: Dict, v16_results: Dict):
    """Compare results from both versions."""
    print(f"\n{'='*60}")
    print("Comparison Summary")
    print(f"{'='*60}\n")
    
    all_paths = set(v13_results.keys()) | set(v16_results.keys())
    
    differences = []
    matches = []
    
    for path in sorted(all_paths):
        v13 = v13_results.get(path, {})
        v16 = v16_results.get(path, {})
        
        v13_status = v13.get("status", "N/A")
        v16_status = v16.get("status", "N/A")
        
        if v13_status != v16_status:
            differences.append({
                "path": path,
                "v13": v13_status,
                "v16": v16_status,
            })
            print(f"⚠️  {path}:")
            print(f"   v13: {v13_status}")
            print(f"   v16: {v16_status}")
        else:
            matches.append(path)
    
    print(f"\n✅ Matching endpoints: {len(matches)}")
    print(f"⚠️  Different endpoints: {len(differences)}")
    
    return differences, matches


def main():
    """Main analysis function."""
    if len(sys.argv) < 5:
        print("Usage: python analyze_op_api_diff.py <v13_url> <v13_token> <v16_url> <v16_token>")
        print("\nExample:")
        print("  python analyze_op_api_diff.py http://localhost:8081 <token> http://localhost:8080 <token>")
        sys.exit(1)
    
    v13_url = sys.argv[1]
    v13_token = sys.argv[2]
    v16_url = sys.argv[3]
    v16_token = sys.argv[4]
    
    print("OpenProject API Version Comparison Tool")
    print("=" * 60)
    
    # Analyze v13
    v13_results = analyze_version(v13_url, v13_token, "OpenProject v13")
    
    # Analyze v16
    v16_results = analyze_version(v16_url, v16_token, "OpenProject v16")
    
    # Compare
    differences, matches = compare_results(v13_results, v16_results)
    
    # Recommendations
    print(f"\n{'='*60}")
    print("Recommendations")
    print(f"{'='*60}\n")
    
    if len(differences) == 0:
        print("✅ No API differences detected. Single codebase should work.")
    elif len(differences) <= 3:
        print("⚠️  Minor differences detected. Recommend:")
        print("   - Support both versions in one file with version detection")
        print("   - Use conditional logic for different endpoints")
    else:
        print("❌ Significant differences detected. Recommend:")
        print("   - Consider separate files or version-specific adapters")
        print("   - Or implement a version abstraction layer")
    
    print("\nKey endpoints used in import_work_packages.py:")
    key_endpoints = [
        "/users",
        "/projects",
        "/types",
        "/work_packages",
        "/time_entries",
        "/time_entries/activities",
        "/memberships",
    ]
    for endpoint in key_endpoints:
        v13_status = v13_results.get(endpoint, {}).get("status", "N/A")
        v16_status = v16_results.get(endpoint, {}).get("status", "N/A")
        status = "✅" if v13_status == v16_status else "⚠️"
        print(f"  {status} {endpoint}: v13={v13_status}, v16={v16_status}")


if __name__ == "__main__":
    main()


