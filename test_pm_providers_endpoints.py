#!/usr/bin/env python3
"""
Test PM Provider Endpoints from Database

This script automatically tests API endpoints for all configured providers
in the database, validating Epics, Components, Labels, and Workflows APIs.

Usage:
    python test_pm_providers_endpoints.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.orm_models import PMProviderConnection
from src.config.loader import get_str_env
from test_pm_api_endpoints import test_jira_endpoints, test_openproject_endpoints


def test_all_providers():
    """Test endpoints for all active providers in database"""
    
    db_url = get_str_env(
        'DATABASE_URL',
        'postgresql://user:password@localhost:5432/deerflow'
    )
    
    try:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        providers = session.query(PMProviderConnection).filter(
            PMProviderConnection.is_active.is_(True)
        ).all()
        
        if not providers:
            print("❌ No active providers found in database")
            print("   Please add providers first using the provider management UI")
            return
        
        print(f"\n✅ Found {len(providers)} active provider(s)\n")
        
        for provider in providers:
            print("=" * 80)
            print(f"Testing Provider: {provider.name} ({provider.provider_type})")
            print("=" * 80)
            
            try:
                if provider.provider_type.lower() == 'jira':
                    if not provider.username or not provider.api_token:
                        print("⚠️  Skipping: Missing username or API token")
                        continue
                    
                    # Try to get project key from first project
                    # For now, test without project key (will test general endpoints)
                    test_jira_endpoints(
                        base_url=provider.base_url,
                        email=provider.username,
                        api_token=provider.api_token,
                        project_key=None  # Will test general endpoints
                    )
                
                elif provider.provider_type.lower() == 'openproject':
                    if not provider.api_key:
                        print("⚠️  Skipping: Missing API key")
                        continue
                    
                    test_openproject_endpoints(
                        base_url=provider.base_url,
                        api_key=provider.api_key,
                        project_id=None  # Will test general endpoints
                    )
                
                else:
                    print(f"⚠️  Provider type '{provider.provider_type}' not yet supported for endpoint testing")
            
            except Exception as e:
                print(f"❌ Error testing provider {provider.name}: {e}")
                import traceback
                traceback.print_exc()
            
            print("\n")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print("   Make sure DATABASE_URL is set correctly")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_all_providers()

