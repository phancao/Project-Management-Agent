#!/usr/bin/env python3
"""Direct test of JIRA project listing"""
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_jira_directly():
    """Test JIRA provider directly"""
    try:
        from database.connection import get_db_session
        from src.server.pm_handler import PMHandler
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        # Create handler in multi-provider mode
        handler = PMHandler.from_db_session(db)
        logger.info(f"Handler mode: {handler._mode}")
        
        # Get all active providers
        providers = handler._get_active_providers()
        logger.info(f"Active providers: {len(providers)}")
        
        # Find JIRA provider
        jira_providers = [p for p in providers if p.provider_type.upper() == 'JIRA']
        logger.info(f"JIRA providers found: {len(jira_providers)}")
        
        if not jira_providers:
            logger.error("❌ No JIRA providers found!")
            return False
        
        # Test each JIRA provider
        for jira_provider in jira_providers:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing JIRA provider: {jira_provider.id}")
            logger.info(f"  Base URL: {jira_provider.base_url}")
            logger.info(f"  Username: {jira_provider.username}")
            logger.info(f"  Is Active: {jira_provider.is_active}")
            logger.info(f"{'='*60}\n")
            
            try:
                # Create instance
                instance = handler._create_provider_instance(jira_provider)
                logger.info("✅ Provider instance created")
                
                # List projects
                logger.info("Calling list_projects()...")
                projects = await instance.list_projects()
                logger.info(f"✅ Got {len(projects)} projects from JIRA")
                
                for i, p in enumerate(projects[:10], 1):  # Show first 10
                    logger.info(f"  {i}. {p.name} (ID: {p.id})")
                
                if len(projects) > 10:
                    logger.info(f"  ... and {len(projects) - 10} more")
                
            except Exception as e:
                logger.error(f"❌ Error: {e}", exc_info=True)
                return False
        
        # Now test the handler's list_all_projects
        logger.info(f"\n{'='*60}")
        logger.info("Testing handler.list_all_projects()...")
        logger.info(f"{'='*60}\n")
        all_projects = await handler.list_all_projects()
        
        logger.info(f"Total projects from handler: {len(all_projects)}")
        
        # Group by provider
        jira_projects = [p for p in all_projects if p.get('provider_type', '').upper() == 'JIRA']
        logger.info(f"JIRA projects in combined list: {len(jira_projects)}")
        
        for p in jira_projects[:10]:
            logger.info(f"  - {p['name']} (ID: {p['id']})")
        
        return len(jira_projects) > 0
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = asyncio.run(test_jira_directly())
    sys.exit(0 if success else 1)
