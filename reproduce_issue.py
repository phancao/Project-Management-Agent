import asyncio
import os
import logging
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from src.pm_providers.openproject_v13 import OpenProjectV13Provider
from src.pm_providers.models import PMProviderConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_list_tasks():
    # Get API key from env
    api_key = os.environ.get("OPENPROJECT_API_KEY")
    if not api_key:
        print("Error: OPENPROJECT_API_KEY not set")
        return

    # Configuration
    project_id = "8eedf4f4-6c0e-4061-bca2-4dc10a118f7a:478"
    config = PMProviderConfig(
        base_url="http://host.docker.internal:8083",
        api_key=api_key,
        project_id=project_id
    )
    
    provider = OpenProjectV13Provider(config)
    
    print(f"Testing list_tasks with project_id: {project_id}")
    
    try:
        tasks = await provider.list_tasks(project_id=project_id)
        print(f"Success! Found {len(tasks)} tasks")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_list_tasks())
