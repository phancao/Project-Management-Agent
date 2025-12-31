#!/usr/bin/env python3
"""Fix JIRA API token in database"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.orm_models import PMProviderConnection
from backend.config.loader import get_str_env

load_dotenv()

db_url = get_str_env("DATABASE_URL", "postgresql://pm_user:pm_password@localhost:5432/project_management")
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

try:
    jira_token = os.getenv('JIRA_API_TOKEN')
    if not jira_token:
        print("❌ JIRA_API_TOKEN not found in .env")
        exit(1)
    
    provider = session.query(PMProviderConnection).filter_by(provider_type='jira').first()
    if not provider:
        print("❌ JIRA provider not found")
        exit(1)
    
    provider.api_token = jira_token
    session.commit()
    print(f"✅ Successfully updated JIRA API token")
    print(f"   Provider: {provider.name}")
    print(f"   Token length: {len(jira_token)} characters")
finally:
    session.close()
