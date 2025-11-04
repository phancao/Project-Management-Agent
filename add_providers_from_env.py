#!/usr/bin/env python3
"""
Script to add PM providers from .env file to the database
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database.orm_models import PMProviderConnection, Base
from src.config.loader import get_str_env

# Load environment variables
load_dotenv()

def get_database_url():
    """Get database URL from environment"""
    db_url = get_str_env("DATABASE_URL", "postgresql://user:password@localhost:5432/deerflow")
    return db_url

def add_providers():
    """Add providers from .env to database"""
    db_url = get_database_url()
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get JIRA configuration
        jira_url = os.getenv('JIRA_BASE_URL')
        jira_token = os.getenv('JIRA_API_TOKEN')
        jira_email = os.getenv('JIRA_EMAIL', '').split('#')[0].strip()
        
        # Get OpenProject configuration
        openproject_url = os.getenv('OPENPROJECT_URL')
        openproject_key = os.getenv('OPENPROJECT_API_KEY')
        
        # Check if providers already exist
        existing_jira = session.query(PMProviderConnection).filter_by(
            provider_type='jira',
            base_url=jira_url
        ).first()
        
        existing_openproject = session.query(PMProviderConnection).filter_by(
            provider_type='openproject',
            base_url=openproject_url
        ).first()
        
        providers_added = []
        
        # Add JIRA provider if not exists
        if not existing_jira and jira_url and jira_token:
            # For JIRA, username should be email if provided
            username = jira_email if jira_email and jira_email != 'your-email@example.com' else None
            
            jira_provider = PMProviderConnection(
                name=f"JIRA - {jira_url}",
                provider_type='jira',
                base_url=jira_url,
                api_token=jira_token,
                username=username
            )
            session.add(jira_provider)
            providers_added.append(f"JIRA ({jira_url})")
            print(f"✅ Adding JIRA provider: {jira_url}")
        elif existing_jira:
            print(f"⚠️  JIRA provider already exists: {jira_url}")
        else:
            print(f"⚠️  Skipping JIRA - missing configuration")
        
        # Add OpenProject provider if not exists
        if not existing_openproject and openproject_url and openproject_key:
            openproject_provider = PMProviderConnection(
                name=f"OpenProject - {openproject_url}",
                provider_type='openproject',
                base_url=openproject_url,
                api_key=openproject_key
            )
            session.add(openproject_provider)
            providers_added.append(f"OpenProject ({openproject_url})")
            print(f"✅ Adding OpenProject provider: {openproject_url}")
        elif existing_openproject:
            print(f"⚠️  OpenProject provider already exists: {openproject_url}")
        else:
            print(f"⚠️  Skipping OpenProject - missing configuration")
        
        if providers_added:
            session.commit()
            print(f"\n✅ Successfully added {len(providers_added)} provider(s):")
            for provider in providers_added:
                print(f"   - {provider}")
        else:
            print("\n⚠️  No new providers added (all already exist or missing configuration)")
            session.rollback()
            
    except Exception as e:
        session.rollback()
        print(f"❌ Error adding providers: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    add_providers()
