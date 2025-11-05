#!/usr/bin/env python3
"""Debug script to test project listing from all providers"""
import asyncio
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_list_projects():
    """Test listing projects from all providers"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        # Get database session
        db_gen = get_db_session()
        db = next(db_gen)
        
        # Create PM handler in multi-provider mode
        logger.info("Creating PM handler in multi-provider mode...")
        handler = PMHandler.from_db_session(db)
        
        logger.info(f"Handler mode: {handler._mode}")
        
        # Get active providers
        providers = handler._get_active_providers()
        logger.info(f"Active providers found: {len(providers)}")
        for p in providers:
            logger.info(f"  - {p.provider_type} (ID: {p.id}, active: {p.is_active}, base_url: {p.base_url})")
        
        # Test listing projects
        logger.info("\nTesting list_all_projects()...")
        projects = await handler.list_all_projects()
        
        logger.info(f"\nTotal projects found: {len(projects)}")
        for project in projects:
            logger.info(f"  - {project['name']} (ID: {project['id']}, Status: {project['status']})")
        
        # Group by provider
        by_provider = {}
        for project in projects:
            if ':' in project['id']:
                provider_id = project['id'].split(':')[0]
            else:
                provider_id = 'unknown'
            if provider_id not in by_provider:
                by_provider[provider_id] = []
            by_provider[provider_id].append(project)
        
        logger.info("\nProjects by provider:")
        for provider_id, projs in by_provider.items():
            logger.info(f"  Provider {provider_id}: {len(projs)} project(s)")
        
        # Test each provider individually
        logger.info("\nTesting each provider individually...")
        for provider in providers:
            try:
                logger.info(f"\nTesting provider {provider.id} ({provider.provider_type})...")
                instance = handler._create_provider_instance(provider)
                provider_projects = await instance.list_projects()
                logger.info(f"  ✅ Success: {len(provider_projects)} project(s) found")
                for p in provider_projects[:5]:  # Show first 5
                    logger.info(f"    - {p.name} (ID: {p.id})")
            except Exception as e:
                logger.error(f"  ❌ Error: {e}", exc_info=True)
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_list_projects())
    sys.exit(0 if success else 1)
