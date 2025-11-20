#!/usr/bin/env python3
"""Script to update JIRA provider email/username in the database"""
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.orm_models import PMProviderConnection
from backend.config.loader import get_str_env

load_dotenv()

def get_database_url():
    """Get database URL from environment"""
    db_url = get_str_env(
        "DATABASE_URL",
        "postgresql://pm_user:pm_password@localhost:5432/project_management"
    )
    return db_url

def update_jira_email():
    """Update JIRA provider email/username"""
    db_url = get_database_url()
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get JIRA email from environment or prompt
        jira_email = os.getenv('JIRA_EMAIL', '').split('#')[0].strip()
        
        # Check command line argument
        if len(sys.argv) > 1:
            jira_email = sys.argv[1].strip()
        
        # Remove placeholder value
        if jira_email == 'your-email@example.com' or not jira_email:
            print("⚠️  JIRA_EMAIL in .env is set to placeholder value.")
            print("Usage: python update_jira_email.py your-email@example.com")
            print("\nOr update .env file with:")
            print("   JIRA_EMAIL=your-actual-email@example.com")
            sys.exit(1)
        
        # Find JIRA provider
        jira_provider = session.query(PMProviderConnection).filter_by(
            provider_type='jira'
        ).first()
        
        if not jira_provider:
            print("❌ JIRA provider not found in database.")
            print("Please run scripts/utils/add_providers_from_env.py first.")
            sys.exit(1)
        
        # Update username/email
        old_email = jira_provider.username or "(not set)"
        jira_provider.username = jira_email
        
        session.commit()
        
        print(f"✅ Successfully updated JIRA provider email:")
        print(f"   Old: {old_email}")
        print(f"   New: {jira_email}")
        print(f"\nProvider details:")
        print(f"   Name: {jira_provider.name}")
        print(f"   Base URL: {jira_provider.base_url}")
        print(f"   Type: {jira_provider.provider_type}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error updating JIRA email: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    update_jira_email()
