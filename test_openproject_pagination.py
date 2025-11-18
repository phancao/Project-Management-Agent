#!/usr/bin/env python3
"""
Test script to verify OpenProject v13 pagination for list_tasks

This script tests:
1. Whether pagination is needed (check total count vs returned count)
2. Whether tasks #85982, #85989, #85990, #87052 are found with pagination
3. Whether sprint_id extraction works correctly for those tasks
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

from src.pm_providers.openproject_v13 import OpenProjectV13Provider
from src.pm_providers.models import PMProviderConfig

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
        from src.config.loader import get_str_env
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

PROJECT_ID = "478"  # AutoFlow QA project ID
SPRINT_4_ID = "613"  # Sprint 4 ID

# Specific tasks the user mentioned
TASK_IDS_TO_FIND = ["85982", "85989", "85990", "87052"]


def get_provider():
    """Create OpenProject v13 provider instance"""
    if not OPENPROJECT_API_KEY:
        print("❌ ERROR: OPENPROJECT_API_KEY not found")
        print("   Set it with: export OPENPROJECT_API_KEY='your_token_here'")
        sys.exit(1)
    
    print(f"\n🔑 Using API key (length: {len(OPENPROJECT_API_KEY)}, preview: {OPENPROJECT_API_KEY[:10]}...{OPENPROJECT_API_KEY[-10:]})")
    
    config = PMProviderConfig(
        provider_type="openproject_v13",
        base_url=OPENPROJECT_URL,
        api_key=OPENPROJECT_API_KEY
    )
    return OpenProjectV13Provider(config)


def test_single_page():
    """Test fetching tasks WITHOUT pagination (current implementation)"""
    print("\n" + "="*80)
    print("TEST 1: Single Page Fetch (Current Implementation)")
    print("="*80)
    
    provider = get_provider()
    url = f"{provider.base_url}/api/v3/work_packages"
    
    filters = [{
        "project": {"operator": "=", "values": [PROJECT_ID]}
    }]
    
    params = {
        "filters": json.dumps(filters),
        "include": "priority,status,assignee,project,version,parent"
    }
    
    print(f"📡 Making request to: {url}")
    print(f"   Headers: Authorization={'Basic ***' if provider.headers.get('Authorization') else 'None'}")
    
    response = requests.get(url, headers=provider.headers, params=params, timeout=30)
    
    # Check response before raising
    if response.status_code == 401:
        print(f"❌ 401 Unauthorized - Authentication failed")
        print(f"   Response: {response.text[:200]}")
        print(f"\n⚠️  Authentication failed. The API key in the database might be different")
        print(f"   from the one that's working in the application.")
        print(f"\n   To fix this:")
        print(f"   1. Check server logs for the working token preview (e741...0a5a)")
        print(f"   2. Update the provider's API key in the database to match")
        print(f"   3. Or set OPENPROJECT_API_KEY environment variable with the working key")
        print(f"\n   For now, let's continue to test pagination logic...")
        raise requests.exceptions.HTTPError(f"401 Client Error: Unauthorized")
    
    data = response.json()
    tasks_data = data.get("_embedded", {}).get("elements", [])
    total_count = data.get("count", len(tasks_data))
    
    print(f"✅ API Response Status: {response.status_code}")
    print(f"📊 Total tasks reported by API: {total_count}")
    print(f"📦 Tasks returned (first page): {len(tasks_data)}")
    
    if total_count > len(tasks_data):
        print(f"⚠️  PAGINATION NEEDED: {total_count - len(tasks_data)} tasks are missing!")
    else:
        print("✅ All tasks fit in one page")
    
    # Check for specific tasks
    found_tasks = []
    for task in tasks_data:
        task_id = str(task.get("id", ""))
        if task_id in TASK_IDS_TO_FIND:
            found_tasks.append(task_id)
            # Extract sprint_id
            links = task.get("_links", {})
            version_href = links.get("version", {}).get("href")
            sprint_id = None
            if version_href:
                sprint_id = version_href.split("/")[-1]
            
            print(f"  ✅ Found task #{task_id}: sprint_id={sprint_id}")
    
    missing_tasks = [tid for tid in TASK_IDS_TO_FIND if tid not in found_tasks]
    if missing_tasks:
        print(f"  ❌ Missing tasks: {missing_tasks}")
    
    # Check sprint_ids in returned tasks
    sprint_ids = set()
    for task in tasks_data:
        links = task.get("_links", {})
        version_href = links.get("version", {}).get("href")
        if version_href:
            sprint_id = version_href.split("/")[-1]
            sprint_ids.add(sprint_id)
    
    print(f"\n📋 Sprint IDs found in returned tasks: {sorted(sprint_ids)}")
    print(f"🔍 Looking for Sprint 4 (ID: {SPRINT_4_ID})")
    if SPRINT_4_ID in sprint_ids:
        print(f"  ✅ Sprint 4 found in returned tasks")
    else:
        print(f"  ❌ Sprint 4 NOT found in returned tasks")
    
    return total_count, len(tasks_data), found_tasks, missing_tasks


def test_with_pagination():
    """Test fetching tasks WITH pagination"""
    print("\n" + "="*80)
    print("TEST 2: Pagination Fetch (Proposed Solution)")
    print("="*80)
    
    provider = get_provider()
    url = f"{provider.base_url}/api/v3/work_packages"
    all_tasks = []
    
    filters = [{
        "project": {"operator": "=", "values": [PROJECT_ID]}
    }]
    
    params = {
        "filters": json.dumps(filters),
        "pageSize": 100,
        "include": "priority,status,assignee,project,version,parent"
    }
    
    page_num = 1
    while url:
        print(f"  📄 Fetching page {page_num}...")
        response = requests.get(url, headers=provider.headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        tasks_data = data.get("_embedded", {}).get("elements", [])
        all_tasks.extend(tasks_data)
        
        total_count = data.get("count", len(all_tasks))
        print(f"     Page {page_num}: {len(tasks_data)} tasks (total so far: {len(all_tasks)}/{total_count})")
        
        # Check for next page
        links = data.get("_links", {})
        next_link = links.get("nextByOffset") or links.get("next")
        
        if next_link and isinstance(next_link, dict):
            next_href = next_link.get("href")
            if next_href:
                if not next_href.startswith("http"):
                    url = f"{provider.base_url}{next_href}"
                else:
                    url = next_href
                params = {}  # Clear params for subsequent requests
                page_num += 1
            else:
                url = None
        else:
            url = None
    
    print(f"\n✅ Total tasks fetched with pagination: {len(all_tasks)} (from {page_num} page(s))")
    
    # Check for specific tasks
    found_tasks = []
    for task in all_tasks:
        task_id = str(task.get("id", ""))
        if task_id in TASK_IDS_TO_FIND:
            found_tasks.append(task_id)
            # Extract sprint_id
            links = task.get("_links", {})
            version_href = links.get("version", {}).get("href")
            sprint_id = None
            if version_href:
                sprint_id = version_href.split("/")[-1]
            
            print(f"  ✅ Found task #{task_id}: sprint_id={sprint_id}")
            if sprint_id == SPRINT_4_ID:
                print(f"     ✅ Task #{task_id} is in Sprint 4!")
            else:
                print(f"     ⚠️  Task #{task_id} is in Sprint {sprint_id}, not Sprint 4")
    
    missing_tasks = [tid for tid in TASK_IDS_TO_FIND if tid not in found_tasks]
    if missing_tasks:
        print(f"  ❌ Still missing tasks: {missing_tasks}")
    else:
        print(f"  ✅ All target tasks found!")
    
    # Count tasks in Sprint 4
    sprint_4_tasks = []
    for task in all_tasks:
        links = task.get("_links", {})
        version_href = links.get("version", {}).get("href")
        if version_href:
            sprint_id = version_href.split("/")[-1]
            if sprint_id == SPRINT_4_ID:
                task_id = str(task.get("id", ""))
                sprint_4_tasks.append(task_id)
    
    print(f"\n📊 Tasks in Sprint 4 (ID: {SPRINT_4_ID}): {len(sprint_4_tasks)}")
    if sprint_4_tasks:
        print(f"   Task IDs: {sorted(sprint_4_tasks)}")
    
    # Check sprint_ids distribution
    sprint_ids_count = {}
    for task in all_tasks:
        links = task.get("_links", {})
        version_href = links.get("version", {}).get("href")
        if version_href:
            sprint_id = version_href.split("/")[-1]
            sprint_ids_count[sprint_id] = sprint_ids_count.get(sprint_id, 0) + 1
        else:
            sprint_ids_count["None"] = sprint_ids_count.get("None", 0) + 1
    
    print(f"\n📋 Sprint distribution:")
    for sprint_id, count in sorted(sprint_ids_count.items()):
        print(f"   Sprint {sprint_id}: {count} tasks")
    
    return len(all_tasks), found_tasks, len(sprint_4_tasks)


async def main():
    print("="*80)
    print("OpenProject v13 Pagination Test")
    print("="*80)
    print(f"Project ID: {PROJECT_ID}")
    print(f"Sprint 4 ID: {SPRINT_4_ID}")
    print(f"Target tasks: {TASK_IDS_TO_FIND}")
    print(f"OpenProject URL: {OPENPROJECT_URL}")
    if OPENPROJECT_API_KEY:
        print(f"API Key loaded: Yes (length: {len(OPENPROJECT_API_KEY)}, preview: {OPENPROJECT_API_KEY[:10]}...{OPENPROJECT_API_KEY[-10:]})")
    else:
        print(f"API Key loaded: No")
    
    try:
        # Test 1: Single page (current implementation)
        total_count, returned_count, found_single, missing_single = test_single_page()
        
        # Test 2: With pagination (proposed solution)
        # Always test pagination, even if API says all tasks fit in one page
        # (API might not report correct total count)
        print(f"\n⚠️  Testing pagination anyway (API might not report correct total)...")
        paginated_count, found_paginated, sprint_4_count = test_with_pagination()
        
        print("\n" + "="*80)
        print("COMPARISON")
        print("="*80)
        print(f"Single page:  {returned_count} tasks, found {len(found_single)}/{len(TASK_IDS_TO_FIND)} target tasks")
        print(f"With pagination: {paginated_count} tasks, found {len(found_paginated)}/{len(TASK_IDS_TO_FIND)} target tasks")
        print(f"Sprint 4 tasks found: {sprint_4_count}")
        
        if len(found_paginated) > len(found_single):
            print("\n✅ PAGINATION WORKS! More target tasks found with pagination.")
            print("   Recommendation: Implement pagination in list_tasks()")
        elif paginated_count > returned_count:
            print(f"\n✅ PAGINATION WORKS! Fetched {paginated_count - returned_count} more tasks with pagination.")
            print("   Recommendation: Implement pagination in list_tasks()")
        elif sprint_4_count > 0:
            print("\n✅ PAGINATION WORKS! Sprint 4 tasks found.")
            print("   Recommendation: Implement pagination in list_tasks()")
        else:
            print("\n⚠️  Pagination fetched same or fewer tasks.")
            if len(found_single) < len(TASK_IDS_TO_FIND):
                print(f"   ⚠️  Only found {len(found_single)}/{len(TASK_IDS_TO_FIND)} target tasks")
                print("   This might indicate a different issue (wrong project, tasks don't exist, etc.)")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

