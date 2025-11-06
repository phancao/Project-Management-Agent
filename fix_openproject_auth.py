#!/usr/bin/env python3
"""
Script to diagnose and fix OpenProject authentication issues
"""
import os
import sys
import base64
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from database.orm_models import PMProviderConnection
from src.config.loader import get_str_env

# Load environment variables
load_dotenv()


def test_openproject_auth(base_url: str, api_key: str) -> bool:
    """Test OpenProject authentication with given credentials"""
    try:
        auth_string = f"apikey:{api_key}"
        credentials = base64.b64encode(auth_string.encode()).decode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}"
        }
        
        response = requests.get(f"{base_url}/api/v3/projects", headers=headers, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"  ❌ Error testing auth: {e}")
        return False


def diagnose_and_fix():
    """Diagnose OpenProject authentication and provide fix instructions"""
    print("🔍 Diagnosing OpenProject Authentication Issue")
    print("=" * 60)
    
    # Check database
    db_url = get_str_env(
        'DATABASE_URL',
        'postgresql://pm_user:pm_password@localhost:5432/project_management'
    )
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get OpenProject provider
        provider = session.query(PMProviderConnection).filter(
            PMProviderConnection.provider_type == 'openproject'
        ).first()
        
        if not provider:
            print("❌ No OpenProject provider found in database")
            print("\n💡 Solution: Run add_providers_from_env.py to add OpenProject provider")
            return
        
        print(f"\n📋 Current Configuration:")
        print(f"   Provider ID: {provider.id}")
        print(f"   Base URL: {provider.base_url}")
        print(f"   Has API Key: {bool(provider.api_key)}")
        if provider.api_key:
            print(f"   API Key Length: {len(provider.api_key)}")
            print(f"   API Key Preview: {provider.api_key[:20]}...")
        
        # Test current API key
        print(f"\n🧪 Testing Current API Key...")
        if test_openproject_auth(provider.base_url, provider.api_key):
            print("   ✅ Current API key is valid!")
            return
        else:
            print("   ❌ Current API key is invalid or expired")
        
        # Check environment variables
        print(f"\n🔍 Checking Environment Variables...")
        openproject_url = os.getenv('OPENPROJECT_URL')
        openproject_key = os.getenv('OPENPROJECT_API_KEY')
        
        if openproject_url:
            print(f"   OPENPROJECT_URL: {openproject_url}")
        else:
            print(f"   OPENPROJECT_URL: ❌ Not set")
        
        if openproject_key:
            print(f"   OPENPROJECT_API_KEY: {'*' * min(20, len(openproject_key))}... (length: {len(openproject_key)})")
            
            # Test env API key
            print(f"\n🧪 Testing Environment API Key...")
            if test_openproject_auth(openproject_url or provider.base_url, openproject_key):
                print("   ✅ Environment API key is valid!")
                print(f"\n💡 Solution: Update database with environment API key")
                print(f"   Run: python update_openproject_api_key.py")
                
                # Offer to update
                response = input("\n   Would you like to update the database now? (y/n): ")
                if response.lower() == 'y':
                    provider.api_key = openproject_key
                    if openproject_url:
                        provider.base_url = openproject_url
                    session.commit()
                    print("   ✅ Database updated successfully!")
                    return
            else:
                print("   ❌ Environment API key is also invalid")
        else:
            print(f"   OPENPROJECT_API_KEY: ❌ Not set")
        
        # Provide instructions
        print(f"\n" + "=" * 60)
        print("📝 How to Fix OpenProject Authentication")
        print("=" * 60)
        print("\n1. Access OpenProject UI:")
        print(f"   → Open http://localhost:8080 in your browser")
        print("\n2. Create/Login to Admin Account:")
        print("   → If first time, create admin account")
        print("   → Username: admin")
        print("   → Email: admin@example.com")
        print("   → Set a password")
        print("\n3. Generate API Token:")
        print("   → Click your avatar (top right) → My Account")
        print("   → Go to 'Access Token' tab")
        print("   → Click 'Generate Token'")
        print("   → Copy the token (e.g., 'a1b2c3d4e5f6g7h8i9j0')")
        print("\n4. Update .env file:")
        print("   → Add/update these lines:")
        print(f"     OPENPROJECT_URL={provider.base_url}")
        print("     OPENPROJECT_API_KEY=<your-token-here>")
        print("\n   ⚠️  Note: Use the RAW token, NOT base64 encoded")
        print("   The code will handle base64 encoding automatically")
        print("\n5. Update Database:")
        print("   → Run: python update_openproject_api_key.py")
        print("\n6. Restart Backend Server:")
        print("   → The changes will take effect after restart")
        print("=" * 60)
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    diagnose_and_fix()



