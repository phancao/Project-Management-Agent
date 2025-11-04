"""Test JIRA provider to see why projects aren't loading"""
import asyncio
import sys
import os
sys.path.insert(0, '.')

# Load environment
from dotenv import load_dotenv
load_dotenv()

from src.pm_providers.models import PMProviderConfig
from src.pm_providers.builder import build_pm_provider_from_config
from database.connection import get_db_session
from database import crud
from database.orm_models import PMProviderConnection
import uuid

async def test_jira():
    db_gen = get_db_session()
    db = next(db_gen)
    
    try:
        users = crud.get_users(db, limit=1)
        if not users:
            print("No users found")
            return
        user_id = users[0].id
        
        # Get JIRA provider
        connection = db.query(PMProviderConnection).filter(
            PMProviderConnection.provider_type == 'jira',
            PMProviderConnection.created_by == user_id,
            PMProviderConnection.is_active == True
        ).first()
        
        if not connection:
            print("No JIRA provider found")
            return
        
        print(f"Found JIRA provider:")
        print(f"  ID: {connection.id}")
        print(f"  URL: {connection.base_url}")
        print(f"  Username: {connection.username}")
        print(f"  Has API Token: {bool(connection.api_token)}")
        print()
        
        # Build provider config
        config = PMProviderConfig(
            provider_type=connection.provider_type,
            base_url=connection.base_url,
            api_key=connection.api_key,
            api_token=connection.api_token,
            username=connection.username,
            organization_id=connection.organization_id,
            workspace_id=connection.workspace_id,
            additional_config=connection.additional_config or {}
        )
        
        print("Building provider...")
        provider = build_pm_provider_from_config(config)
        if not provider:
            print("❌ Failed to build provider")
            return
        
        print("✅ Provider built successfully")
        print(f"   Type: {type(provider).__name__}")
        print()
        
        print("Calling list_projects()...")
        try:
            projects = await provider.list_projects()
            print(f"✅ list_projects() returned {len(projects)} projects")
            
            if projects:
                print("\nProjects found:")
                for p in projects:
                    print(f"  - {p.name}")
                    print(f"    ID: {p.external_id}")
                    print(f"    Status: {p.status}")
                    print()
            else:
                print("\n⚠️  No projects returned. This could mean:")
                print("  1. The account has no projects")
                print("  2. The API token doesn't have permission to list projects")
                print("  3. Authentication is failing silently")
                
                # Try a direct API call to see what's happening
                print("\nTesting direct API call...")
                import requests
                import base64
                
                auth_string = f"{connection.username}:{connection.api_token}"
                auth_bytes = auth_string.encode('ascii')
                auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
                
                headers = {
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                
                url = f"{connection.base_url}/rest/api/3/project"
                print(f"URL: {url}")
                print(f"Headers: {headers.get('Authorization')[:20]}...")
                
                response = requests.get(url, headers=headers, timeout=10)
                print(f"Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"Response Type: {type(data)}")
                    if isinstance(data, list):
                        print(f"Response Length: {len(data)}")
                        if data:
                            print("First project:")
                            print(f"  {data[0]}")
                    elif isinstance(data, dict):
                        print("Response Keys:", list(data.keys()))
                        if 'values' in data:
                            print(f"Values Length: {len(data['values'])}")
                            if data['values']:
                                print("First project:")
                                print(f"  {data['values'][0]}")
                else:
                    print(f"Error Response: {response.text[:500]}")
                    
        except Exception as e:
            print(f"❌ Error calling list_projects(): {e}")
            import traceback
            traceback.print_exc()
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_jira())
