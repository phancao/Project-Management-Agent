#!/usr/bin/env python3
"""
Test OpenProject v13 API authentication methods directly
"""
import sys
import base64
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.orm_models import PMProviderConnection
from src.config.loader import get_str_env

def test_auth_methods(base_url: str, api_key: str):
    """Test different authentication methods"""
    print(f"\n{'='*60}")
    print(f"Testing OpenProject v13 Authentication")
    print(f"{'='*60}")
    print(f"Base URL: {base_url}")
    print(f"API Key length: {len(api_key)}")
    print(f"API Key preview: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else '***'}")
    print(f"\n{'='*60}\n")
    
    url = f"{base_url}/api/v3/projects"
    
    # Method 1: Basic Auth with apikey:TOKEN
    print("Method 1: Basic Auth (apikey:TOKEN)")
    print("-" * 60)
    auth_string = f"apikey:{api_key}"
    credentials = base64.b64encode(auth_string.encode()).decode()
    headers1 = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {credentials}"
    }
    try:
        response = requests.get(url, headers=headers1, timeout=10)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            projects = data.get("_embedded", {}).get("elements", [])
            print(f"  ✅ SUCCESS! Found {len(projects)} projects")
            for p in projects[:3]:
                print(f"     - {p.get('name')} (ID: {p.get('id')})")
            return True
        else:
            print(f"  ❌ Failed: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print()
    
    # Method 2: Bearer Token
    print("Method 2: Bearer Token")
    print("-" * 60)
    headers2 = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    try:
        response = requests.get(url, headers=headers2, timeout=10)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            projects = data.get("_embedded", {}).get("elements", [])
            print(f"  ✅ SUCCESS! Found {len(projects)} projects")
            for p in projects[:3]:
                print(f"     - {p.get('name')} (ID: {p.get('id')})")
            return True
        else:
            print(f"  ❌ Failed: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print()
    
    # Method 3: Basic Auth with just the token (no apikey: prefix)
    print("Method 3: Basic Auth (TOKEN only, empty username)")
    print("-" * 60)
    auth_string3 = f"{api_key}:"
    credentials3 = base64.b64encode(auth_string3.encode()).decode()
    headers3 = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {credentials3}"
    }
    try:
        response = requests.get(url, headers=headers3, timeout=10)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            projects = data.get("_embedded", {}).get("elements", [])
            print(f"  ✅ SUCCESS! Found {len(projects)} projects")
            for p in projects[:3]:
                print(f"     - {p.get('name')} (ID: {p.get('id')})")
            return True
        else:
            print(f"  ❌ Failed: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print()
    print("❌ All authentication methods failed!")
    return False


def main():
    """Main function"""
    # Get database connection
    db_url = get_str_env(
        "DATABASE_URL",
        "postgresql://pm_user:pm_password@localhost:5432/project_management"
    )
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Find OpenProject v13 provider
        provider = session.query(PMProviderConnection).filter(
            PMProviderConnection.provider_type == 'openproject_v13',
            PMProviderConnection.is_active.is_(True)
        ).first()
        
        if not provider:
            print("❌ OpenProject v13 provider not found in database")
            print("\nLooking for providers with type 'openproject_v13'...")
            all_providers = session.query(PMProviderConnection).filter(
                PMProviderConnection.is_active.is_(True)
            ).all()
            print(f"\nFound {len(all_providers)} active providers:")
            for p in all_providers:
                print(f"  - {p.provider_type}: {p.name} ({p.base_url})")
            sys.exit(1)
        
        base_url = str(provider.base_url).rstrip('/')
        api_key = None
        
        if provider.api_key:
            api_key = str(provider.api_key).strip()
        elif provider.api_token:
            api_key = str(provider.api_token).strip()
        
        if not api_key:
            print("❌ No API key found for OpenProject v13 provider")
            print(f"   Provider: {provider.name}")
            print(f"   Base URL: {provider.base_url}")
            sys.exit(1)
        
        print(f"Found OpenProject v13 provider:")
        print(f"  Name: {provider.name}")
        print(f"  Base URL: {base_url}")
        print(f"  Has API Key: {bool(api_key)}")
        
        # Test authentication methods
        success = test_auth_methods(base_url, api_key)
        
        if success:
            print(f"\n{'='*60}")
            print("✅ Authentication successful!")
            print(f"{'='*60}")
        else:
            print(f"\n{'='*60}")
            print("❌ All authentication methods failed")
            print(f"{'='*60}")
            print("\nPossible issues:")
            print("  1. API key is invalid or expired")
            print("  2. API key doesn't have proper permissions")
            print("  3. OpenProject v13 instance is not accessible")
            print("  4. Token format is incorrect")
            print("\nTo fix:")
            print("  1. Generate a new API token in OpenProject v13:")
            print("     My Account → Access Tokens → Generate Token")
            print("  2. Update the provider configuration with the new token")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()

