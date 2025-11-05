#!/usr/bin/env python3
"""Update OpenProject API key in database"""
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.orm_models import PMProviderConnection
from src.config.loader import get_str_env

load_dotenv()

def update_openproject_key():
    """Update OpenProject API key"""
    db_url = get_str_env("DATABASE_URL", "postgresql://pm_user:pm_password@localhost:5432/project_management")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get API key from environment or command line
        api_key = os.getenv('OPENPROJECT_API_KEY', '').strip()
        
        if len(sys.argv) > 1:
            api_key = sys.argv[1].strip()
        
        if not api_key:
            print("❌ OPENPROJECT_API_KEY not found")
            print("Usage: python update_openproject_key.py <api_key>")
            print("\nOr update .env file with:")
            print("   OPENPROJECT_API_KEY=your-api-key-here")
            sys.exit(1)
        
        provider = session.query(PMProviderConnection).filter_by(provider_type='openproject').first()
        if not provider:
            print("❌ OpenProject provider not found in database")
            sys.exit(1)
        
        old_key = provider.api_key or "(not set)"
        provider.api_key = api_key
        session.commit()
        
        print(f"✅ Successfully updated OpenProject API key")
        print(f"   Provider: {provider.name}")
        print(f"   Base URL: {provider.base_url}")
        print(f"   Old key: {old_key[:20]}..." if len(str(old_key)) > 20 else f"   Old key: {old_key}")
        print(f"   New key: {api_key[:20]}...{api_key[-10:]}")
        print(f"\n⚠️  Note: If authentication still fails, verify:")
        print(f"   1. The API key is correct and not expired")
        print(f"   2. Generate a new key in OpenProject: My Account → Access Token")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error updating OpenProject API key: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    update_openproject_key()
