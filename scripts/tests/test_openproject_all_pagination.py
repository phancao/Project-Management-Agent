#!/usr/bin/env python3
"""
Comprehensive test script to verify OpenProject v13 pagination for ALL listing methods

This script tests pagination for:
1. list_projects
2. list_sprints
3. list_tasks
4. list_users
5. list_epics
6. list_labels
7. list_statuses
8. list_priorities
"""

import asyncio
import os
import sys
import json
import requests
import base64
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pm_providers.openproject_v13 import OpenProjectV13Provider
from pm_providers.models import PMProviderConfig

# Configuration - MUST use https://openproject.bstarsolutions.com
OPENPROJECT_URL = "https://openproject.bstarsolutions.com"
OPENPROJECT_API_KEY = os.getenv("OPENPROJECT_API_KEY", "")

# Get API key from database for the specific URL (handle trailing slash)
# Always try to get from database first, even if env var is set (to use the correct one)
print("🔍 Loading API key from database...")
try:
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from database.orm_models import PMProviderConnection
        from backend.config.loader import get_str_env
        from dotenv import load_dotenv
        
        load_dotenv()
        db_url = get_str_env("DATABASE_URL", "postgresql://pm_user:pm_password@localhost:5432/project_management")
        print(f"🔍 Connecting to database: {db_url.split('@')[-1] if '@' in db_url else 'hidden'}")
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Find OpenProject v13 provider for https://openproject.bstarsolutions.com
        # Handle both with and without trailing slash
        print(f"🔍 Looking for provider: type=openproject_v13, url={OPENPROJECT_URL}")
        all_providers = session.query(PMProviderConnection).filter(
            PMProviderConnection.provider_type == 'openproject_v13'
        ).all()
        
        print(f"   Found {len(all_providers)} openproject_v13 provider(s) in database")
        
        # Find the one matching our URL (handle trailing slash)
        provider = None
        for p in all_providers:
            if p.base_url.rstrip('/') == OPENPROJECT_URL.rstrip('/'):
                provider = p
                print(f"   ✅ Matched provider: {p.base_url} (name: {p.name or 'Unnamed'})")
                break
        
        if not provider and all_providers:
            # Use the first one if exact match not found
            provider = all_providers[0]
            print(f"   ⚠️  No exact URL match, using first available provider: {provider.base_url}")
        
        if provider:
            if provider.api_key:
                OPENPROJECT_API_KEY = str(provider.api_key).strip()
                print(f"✅ Found API key from database")
                print(f"   Provider URL: {provider.base_url}")
                print(f"   Provider Name: {provider.name or 'Unnamed'}")
                print(f"   API Key length: {len(OPENPROJECT_API_KEY)}")
                print(f"   API Key preview: {OPENPROJECT_API_KEY[:10]}...{OPENPROJECT_API_KEY[-10:]}")
            else:
                print(f"⚠️  Provider found but API key is empty")
        else:
            print(f"⚠️  No OpenProject v13 provider found in database")
            if all_providers:
                print(f"   Available providers:")
                for p in all_providers:
                    has_key = "✅" if p.api_key else "❌"
                    match = "🎯" if p.base_url.rstrip('/') == OPENPROJECT_URL.rstrip('/') else "  "
                    print(f"     {match} {has_key} {p.base_url} (name: {p.name or 'Unnamed'}, has_key: {bool(p.api_key)})")
            else:
                print(f"     ❌ No openproject_v13 providers found at all")
        
        session.close()
    except Exception as e:
        print(f"⚠️  Could not load API key from database: {e}")
        import traceback
        traceback.print_exc()
        if not OPENPROJECT_API_KEY:
            print("   Will try to use environment variable or fail with clear error")
except Exception as e:
    print(f"⚠️  Error in database lookup: {e}")
    import traceback
    traceback.print_exc()

# Final check
if not OPENPROJECT_API_KEY:
    print(f"\n❌ ERROR: No API key found!")
    print(f"   Set OPENPROJECT_API_KEY environment variable or ensure provider exists in database")
    sys.exit(1)


def get_provider():
    """Create OpenProject v13 provider instance"""
    config = PMProviderConfig(
        provider_type="openproject_v13",
        base_url=OPENPROJECT_URL,
        api_key=OPENPROJECT_API_KEY
    )
    return OpenProjectV13Provider(config)


def test_pagination_for_endpoint(endpoint_name: str, url: str, params: dict = None):
    """Test pagination for a specific API endpoint"""
    print(f"\n{'='*80}")
    print(f"Testing: {endpoint_name}")
    print(f"{'='*80}")
    
    provider = get_provider()
    
    if params is None:
        params = {"pageSize": 100}
    else:
        params = params.copy()
        if "pageSize" not in params:
            params["pageSize"] = 100
    
    all_items = []
    request_url = url
    page_num = 1
    
    while request_url:
        try:
            print(f"  📄 Fetching page {page_num}...")
            response = requests.get(request_url, headers=provider.headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            items = data.get("_embedded", {}).get("elements", [])
            all_items.extend(items)
            
            total_count = data.get("count", len(all_items))
            print(f"     Page {page_num}: {len(items)} items (total so far: {len(all_items)}/{total_count})")
            
            # Check for next page
            links = data.get("_links", {})
            next_link = links.get("nextByOffset") or links.get("next")
            
            if next_link and isinstance(next_link, dict):
                next_href = next_link.get("href")
                if next_href:
                    if not next_href.startswith("http"):
                        request_url = f"{provider.base_url}{next_href}"
                    else:
                        request_url = next_href
                    params = {}  # Clear params for subsequent requests
                    page_num += 1
                else:
                    request_url = None
            else:
                request_url = None
        except Exception as e:
            print(f"     ❌ Error on page {page_num}: {e}")
            break
    
    print(f"\n  ✅ Total items fetched: {len(all_items)} (from {page_num} page(s))")
    
    if page_num > 1:
        print(f"  ✅ PAGINATION WORKED! Fetched {page_num} pages")
    else:
        print(f"  ℹ️  All items fit in one page")
    
    return len(all_items), page_num


async def test_all_listing_methods():
    """Test all listing methods using the provider"""
    print("\n" + "="*80)
    print("Testing Provider Methods (using async provider methods)")
    print("="*80)
    
    provider = get_provider()
    results = {}
    
    # Test 1: list_projects
    try:
        print(f"\n📋 Testing list_projects()...")
        projects = await provider.list_projects()
        results["list_projects"] = {
            "count": len(projects),
            "status": "✅ Success"
        }
        print(f"   ✅ Found {len(projects)} projects")
    except Exception as e:
        results["list_projects"] = {
            "count": 0,
            "status": f"❌ Error: {e}"
        }
        print(f"   ❌ Error: {e}")
    
    # Test 2: list_sprints
    try:
        print(f"\n📋 Testing list_sprints()...")
        sprints = await provider.list_sprints()
        results["list_sprints"] = {
            "count": len(sprints),
            "status": "✅ Success"
        }
        print(f"   ✅ Found {len(sprints)} sprints")
    except Exception as e:
        results["list_sprints"] = {
            "count": 0,
            "status": f"❌ Error: {e}"
        }
        print(f"   ❌ Error: {e}")
    
    # Test 3: list_tasks
    try:
        print(f"\n📋 Testing list_tasks()...")
        tasks = await provider.list_tasks(project_id="478")
        results["list_tasks"] = {
            "count": len(tasks),
            "status": "✅ Success"
        }
        print(f"   ✅ Found {len(tasks)} tasks")
    except Exception as e:
        results["list_tasks"] = {
            "count": 0,
            "status": f"❌ Error: {e}"
        }
        print(f"   ❌ Error: {e}")
    
    # Test 4: list_users
    try:
        print(f"\n📋 Testing list_users()...")
        users = await provider.list_users()
        results["list_users"] = {
            "count": len(users),
            "status": "✅ Success"
        }
        print(f"   ✅ Found {len(users)} users")
    except Exception as e:
        results["list_users"] = {
            "count": 0,
            "status": f"❌ Error: {e}"
        }
        print(f"   ❌ Error: {e}")
    
    # Test 5: list_epics
    try:
        print(f"\n📋 Testing list_epics()...")
        epics = await provider.list_epics(project_id="478")
        results["list_epics"] = {
            "count": len(epics),
            "status": "✅ Success"
        }
        print(f"   ✅ Found {len(epics)} epics")
    except Exception as e:
        results["list_epics"] = {
            "count": 0,
            "status": f"❌ Error: {e}"
        }
        print(f"   ❌ Error: {e}")
    
    # Test 6: list_labels
    try:
        print(f"\n📋 Testing list_labels()...")
        labels = await provider.list_labels(project_id="478")
        results["list_labels"] = {
            "count": len(labels),
            "status": "✅ Success"
        }
        print(f"   ✅ Found {len(labels)} labels")
    except Exception as e:
        results["list_labels"] = {
            "count": 0,
            "status": f"❌ Error: {e}"
        }
        print(f"   ❌ Error: {e}")
    
    # Test 7: list_statuses
    try:
        print(f"\n📋 Testing list_statuses()...")
        statuses = await provider.list_statuses("task")
        results["list_statuses"] = {
            "count": len(statuses),
            "status": "✅ Success"
        }
        print(f"   ✅ Found {len(statuses)} statuses")
    except Exception as e:
        results["list_statuses"] = {
            "count": 0,
            "status": f"❌ Error: {e}"
        }
        print(f"   ❌ Error: {e}")
    
    # Test 8: list_priorities
    try:
        print(f"\n📋 Testing list_priorities()...")
        priorities = await provider.list_priorities()
        results["list_priorities"] = {
            "count": len(priorities),
            "status": "✅ Success"
        }
        print(f"   ✅ Found {len(priorities)} priorities")
    except Exception as e:
        results["list_priorities"] = {
            "count": 0,
            "status": f"❌ Error: {e}"
        }
        print(f"   ❌ Error: {e}")
    
    return results


async def main():
    print("="*80)
    print("OpenProject v13 Comprehensive Pagination Test")
    print("="*80)
    print(f"OpenProject URL: {OPENPROJECT_URL}")
    if OPENPROJECT_API_KEY:
        print(f"API Key loaded: Yes (length: {len(OPENPROJECT_API_KEY)}, preview: {OPENPROJECT_API_KEY[:10]}...{OPENPROJECT_API_KEY[-10:]})")
    else:
        print(f"API Key loaded: No")
    
    provider = get_provider()
    base_url = provider.base_url
    
    # Test direct API endpoints
    print("\n" + "="*80)
    print("Testing Direct API Endpoints (with pagination)")
    print("="*80)
    
    api_results = {}
    
    # 1. Projects
    api_results["projects"] = test_pagination_for_endpoint(
        "Projects",
        f"{base_url}/api/v3/projects",
        {"pageSize": 100}
    )
    
    # 2. Versions (Sprints)
    api_results["versions"] = test_pagination_for_endpoint(
        "Versions (Sprints)",
        f"{base_url}/api/v3/versions",
        {"pageSize": 100}
    )
    
    # 3. Work Packages (Tasks) - with project filter
    filters = [{"project": {"operator": "=", "values": ["478"]}}]
    api_results["work_packages"] = test_pagination_for_endpoint(
        "Work Packages (Tasks) - Project 478",
        f"{base_url}/api/v3/work_packages",
        {
            "filters": json.dumps(filters),
            "pageSize": 100,
            "include": "priority,status,assignee,project,version,parent"
        }
    )
    
    # 4. Users
    api_results["users"] = test_pagination_for_endpoint(
        "Users",
        f"{base_url}/api/v3/users",
        {"pageSize": 100}
    )
    
    # 5. Statuses
    api_results["statuses"] = test_pagination_for_endpoint(
        "Statuses",
        f"{base_url}/api/v3/statuses",
        {"pageSize": 100}
    )
    
    # 6. Priorities
    api_results["priorities"] = test_pagination_for_endpoint(
        "Priorities",
        f"{base_url}/api/v3/priorities",
        {"pageSize": 100}
    )
    
    # Test provider methods
    method_results = await test_all_listing_methods()
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    print("\n📊 Direct API Endpoint Results:")
    for endpoint, (count, pages) in api_results.items():
        status = "✅" if pages > 1 else "ℹ️"
        print(f"   {status} {endpoint:20s}: {count:4d} items, {pages} page(s)")
    
    print("\n📊 Provider Method Results:")
    for method, result in method_results.items():
        print(f"   {result['status']:3s} {method:20s}: {result['count']:4d} items")
    
    # Compare results
    print("\n🔍 Comparison (API vs Provider):")
    comparisons = {
        "projects": ("projects", "list_projects"),
        "work_packages": ("work_packages", "list_tasks"),
        "users": ("users", "list_users"),
        "statuses": ("statuses", "list_statuses"),
        "priorities": ("priorities", "list_priorities"),
    }
    
    for api_key, (api_name, method_name) in comparisons.items():
        if api_key in api_results and method_name in method_results:
            api_count = api_results[api_key][0]
            method_count = method_results[method_name]["count"]
            match = "✅" if api_count == method_count else "⚠️"
            print(f"   {match} {api_name:20s}: API={api_count:4d}, Method={method_count:4d}")
    
    print("\n" + "="*80)
    print("✅ Pagination test complete!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())

