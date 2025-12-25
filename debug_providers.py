
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append('/Volumes/Data 1/Gravity_ProjectManagementAgent/Project-Management-Agent')

from mcp_server.database.connection import get_mcp_db_session
from mcp_server.core.provider_manager import ProviderManager
from mcp_server.database.models import PMProviderConnection

def check_providers():
    db = next(get_mcp_db_session())
    try:
        manager = ProviderManager(db)
        providers = manager.get_active_providers()
        print(f"Found {len(providers)} active providers:")
        for p in providers:
            key_preview = "None"
            if p.api_key:
                key_preview = f"{p.api_key[:8]}...{p.api_key[-4:]}"
            print(f"- Type: {p.provider_type}, ID: {p.id}, Key: {key_preview}")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_providers()
