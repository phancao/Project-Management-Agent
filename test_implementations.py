#!/usr/bin/env python3
"""
Quick test of implemented PM provider methods
"""
import sys
import asyncio
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.orm_models import PMProviderConnection
from src.config.loader import get_str_env
from src.pm_providers.builder import build_pm_provider


async def test_provider_methods(provider_type, provider_config):
    """Test all implemented methods for a provider"""
    print(f"\n{'='*80}")
    print(f"Testing {provider_type.upper()} Provider Implementations")
    print(f"{'='*80}\n")
    
    provider = build_pm_provider(provider_config)
    if not provider:
        print(f"❌ Failed to build {provider_type} provider")
        return
    
    # Test with first available project
    projects = await provider.list_projects()
    if not projects:
        print(f"⚠️  No projects found for {provider_type}")
        return
    
    test_project = projects[0]
    print(f"📋 Using project: {test_project.name} (ID: {test_project.id})\n")
    
    results = {}
    
    # Test Epics
    try:
        epics = await provider.list_epics(project_id=test_project.id)
        results['epics'] = ('✅', len(epics))
        print(f"✅ list_epics(): Found {len(epics)} epics")
        if epics:
            print(f"   Example: {epics[0].name}")
    except Exception as e:
        results['epics'] = ('❌', str(e)[:100])
        print(f"❌ list_epics(): {e}")
    
    # Test Components
    try:
        components = await provider.list_components(project_id=test_project.id)
        results['components'] = ('✅', len(components))
        print(f"✅ list_components(): Found {len(components)} components")
        if components:
            print(f"   Example: {components[0].name}")
    except Exception as e:
        results['components'] = ('❌', str(e)[:100])
        print(f"❌ list_components(): {e}")
    
    # Test Labels
    try:
        labels = await provider.list_labels(project_id=test_project.id)
        results['labels'] = ('✅', len(labels))
        print(f"✅ list_labels(): Found {len(labels)} labels")
        if labels:
            print(f"   Example: {labels[0].name}")
    except Exception as e:
        results['labels'] = ('❌', str(e)[:100])
        print(f"❌ list_labels(): {e}")
    
    # Test Statuses
    try:
        statuses = await provider.list_statuses(entity_type="task", project_id=test_project.id)
        results['statuses'] = ('✅', len(statuses))
        print(f"✅ list_statuses(): Found {len(statuses)} statuses")
        if statuses:
            print(f"   Examples: {', '.join(statuses[:5])}")
    except Exception as e:
        results['statuses'] = ('❌', str(e)[:100])
        print(f"❌ list_statuses(): {e}")
    
    print(f"\n{'='*80}")
    print(f"Summary for {provider_type.upper()}:")
    for method, (status, result) in results.items():
        print(f"  {method:15} {status} {result}")
    print(f"{'='*80}\n")
    
    return results


async def main():
    """Test all active providers"""
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
            print("❌ No active providers found")
            return
        
        for provider in providers:
            await test_provider_methods(
                provider.provider_type,
                provider
            )
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

