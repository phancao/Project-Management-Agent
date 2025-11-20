#!/usr/bin/env python3
"""
Setup Backend MCP API Key

Creates a system user and API key for the backend service to authenticate with the MCP server.

Usage:
    python scripts/setup_backend_mcp_api_key.py
    
    Or with custom key:
    python scripts/setup_backend_mcp_api_key.py --api-key mcp_YOUR_KEY_HERE
"""

import argparse
import sys
from pathlib import Path
from uuid import uuid4, UUID

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.database.connection import get_mcp_db_session
from mcp_server.database.models import User, UserMCPAPIKey
from mcp_server.auth import generate_mcp_api_key
from datetime import datetime


def create_system_user_and_api_key(api_key: str | None = None) -> str:
    """
    Create a system user and API key for backend authentication.
    
    Args:
        api_key: Optional API key to use. If None, generates a new one.
        
    Returns:
        The API key (either provided or generated)
    """
    db = next(get_mcp_db_session())
    
    try:
        # System user UUID (fixed for consistency)
        SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")
        
        # Check if system user exists
        system_user = db.query(User).filter(User.id == SYSTEM_USER_ID).first()
        
        if not system_user:
            # Create system user
            system_user = User(
                id=SYSTEM_USER_ID,
                email="system@backend",
                name="Backend Service",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(system_user)
            db.commit()
            print(f"✅ Created system user: {system_user.email}")
        else:
            print(f"✅ System user already exists: {system_user.email}")
        
        # Generate API key if not provided
        if not api_key:
            api_key = generate_mcp_api_key()
            print(f"✅ Generated new API key: {api_key[:20]}...")
        else:
            print(f"✅ Using provided API key: {api_key[:20]}...")
        
        # Check if API key already exists
        existing_key = db.query(UserMCPAPIKey).filter(
            UserMCPAPIKey.api_key == api_key
        ).first()
        
        if existing_key:
            if existing_key.is_active:
                print(f"⚠️  API key already exists and is active")
                print(f"   Key: {api_key}")
                print(f"   User: {existing_key.user_id}")
                return api_key
            else:
                # Reactivate the key
                existing_key.is_active = True
                existing_key.updated_at = datetime.utcnow()
                db.commit()
                print(f"✅ Reactivated existing API key")
                return api_key
        
        # Create new API key
        key_record = UserMCPAPIKey(
            user_id=SYSTEM_USER_ID,
            api_key=api_key,
            name="Backend Service API Key",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(key_record)
        db.commit()
        db.refresh(key_record)
        
        print(f"✅ Created API key record in database")
        print(f"\n📋 API Key Details:")
        print(f"   Key: {api_key}")
        print(f"   User ID: {SYSTEM_USER_ID}")
        print(f"   Name: Backend Service API Key")
        print(f"   Status: Active")
        
        return api_key
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Setup backend MCP API key for authentication"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="API key to use (if not provided, generates a new one)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Backend MCP API Key Setup")
    print("=" * 60)
    print()
    
    try:
        api_key = create_system_user_and_api_key(args.api_key)
        
        print()
        print("=" * 60)
        print("✅ Setup Complete!")
        print("=" * 60)
        print()
        print("Next steps:")
        print(f"1. Add to docker-compose.yml:")
        print(f"   PM_MCP_API_KEY={api_key}")
        print()
        print("2. Or add to .env file:")
        print(f"   PM_MCP_API_KEY={api_key}")
        print()
        print("3. Restart backend service:")
        print("   docker-compose restart api")
        print()
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

