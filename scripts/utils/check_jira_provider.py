#!/usr/bin/env python3
"""Check JIRA provider configuration in database"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.orm_models import PMProviderConnection
from backend.config.loader import get_str_env

db_url = get_str_env("DATABASE_URL", "postgresql://pm_user:pm_password@localhost:5432/project_management")
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

try:
    provider = session.query(PMProviderConnection).filter_by(provider_type='jira').first()
    if provider:
        print("JIRA Provider Configuration:")
        print(f"  Name: {provider.name}")
        print(f"  Base URL: {provider.base_url}")
        print(f"  Username (email): {provider.username}")
        print(f"  API Token: {'*' * 20 if provider.api_token else 'NOT SET'}")
        print(f"  Is Active: {provider.is_active}")
        print(f"  Created: {provider.created_at}")
    else:
        print("❌ JIRA provider not found")
finally:
    session.close()
