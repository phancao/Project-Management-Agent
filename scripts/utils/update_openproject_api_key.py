#!/usr/bin/env python3
"""
Script to update OpenProject provider API key from .env file
"""
import os
import sys
import traceback

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.orm_models import PMProviderConnection
from backend.config.loader import get_str_env

# Load environment variables
load_dotenv()


def update_openproject_api_key():
    """Update OpenProject provider API key from .env"""
    db_url = get_str_env(
        'DATABASE_URL',
        'postgresql://user:password@localhost:5432/deerflow'
    )
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get OpenProject configuration from .env
        openproject_url = os.getenv('OPENPROJECT_URL')
        openproject_key = os.getenv('OPENPROJECT_API_KEY')

        if not openproject_url or not openproject_key:
            print("❌ Missing OPENPROJECT_URL or OPENPROJECT_API_KEY in .env")
            return

        # Find OpenProject provider
        provider = session.query(PMProviderConnection).filter(
            PMProviderConnection.provider_type == 'openproject',
            PMProviderConnection.base_url == openproject_url
        ).first()

        if not provider:
            print(
                f"❌ OpenProject provider not found for URL: "
                f"{openproject_url}"
            )
            return

        # Update API key
        provider.api_key = openproject_key
        session.commit()

        print("✅ Updated OpenProject provider API key")
        print(f"   URL: {openproject_url}")
        print(f"   Has API Key: {bool(provider.api_key)}")

    except Exception as e:
        session.rollback()
        print(f"❌ Error updating provider: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    update_openproject_api_key()
