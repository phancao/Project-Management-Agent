#!/usr/bin/env python3
"""Check existing providers in database"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from database.orm_models import PMProviderConnection  # noqa: E402
from backend.config.loader import get_str_env  # noqa: E402


def check_providers():
    db_url = get_str_env(
        'DATABASE_URL',
        'postgresql://user:password@localhost:5432/deerflow'
    )
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        providers = session.query(PMProviderConnection).all()
        print(f'\n✅ Found {len(providers)} provider(s):\n')
        for p in providers:
            print(f'  📦 {p.name}')
            print(f'     Type: {p.provider_type}')
            print(f'     URL: {p.base_url}')
            if p.provider_type == 'jira':
                print(f'     Username: {p.username or "(not set)"}')
                print(f'     Has API Token: {bool(p.api_token)}')
            elif p.provider_type == 'openproject':
                print(f'     Has API Key: {bool(p.api_key)}')
            print()
    finally:
        session.close()


if __name__ == "__main__":
    check_providers()
