#!/usr/bin/env python3
"""
Cleanup database script - Remove all PM data for fresh testing
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://pm_user:pm_password@localhost:5432/project_management")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def cleanup_database():
    """Clean all PM tables"""
    print("🧹 Cleaning database...")
    
    # Truncate tables in order (respecting FK dependencies)
    tables = [
        "sprint_tasks",
        "sprints",
        "tasks",
        "projects",
    ]
    
    for table in tables:
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"TRUNCATE TABLE {table} CASCADE;"))
                conn.commit()
                print(f"✅ Cleaned {table}")
        except Exception as e:
            print(f"⚠️  {table}: {e}")
    
    print("\n✅ Database cleaned successfully!")

if __name__ == "__main__":
    cleanup_database()

