
import asyncio
import os
import sys
import logging

# Ensure we can import from the project
sys.path.append(os.getcwd())

from pm_service.client.async_client import AsyncPMServiceClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_tasks():
    # Use the service URL from docker-compose or default
    # If running from host, we might need to point to the port exposed by docker
    # Assuming pm-service is running on port 8000 (as per docker-compose usually)
    # But wait, backend-api is 8001. PM Service might be internal only?
    # Docker compose:
    # pm-service: port 8000:8000
    # backend-api: port 8001:8001
    
    base_url = os.environ.get("PM_SERVICE_URL", "http://pm-service:8001") 
    
    logger.info(f"Connecting to PM Service at {base_url}...")
    
    async with AsyncPMServiceClient(base_url=base_url) as client:
        # 1. List Projects
        logger.info("Listing projects...")
        try:
            projects_response = await client.list_projects()
            projects = projects_response.get("items", [])
            logger.info(f"Found {len(projects)} projects.")
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            return

        target_project = None
        for p in projects:
            if p.get("name") == "AutoFlow QA":
                target_project = p
                break
        
        if not target_project:
            logger.error("Project 'AutoFlow QA' not found!")
            # Fallback to first project
            if projects:
                target_project = projects[0]
                logger.info(f"Falling back to project: {target_project.get('name')}")
            else:
                return

        project_id = target_project.get("id")
        logger.info(f"Target Project: {target_project.get('name')} (ID: {project_id})")

        # 2. List Sprints
        logger.info(f"Listing sprints for project {project_id}...")
        sprints_response = await client.list_sprints(project_id=project_id)
        sprints = sprints_response.get("items", [])
        logger.info(f"Found {len(sprints)} sprints.")
        for s in sprints:
            logger.info(f" - Sprint: {s.get('name')} (ID: {s.get('id')}, Status: {s.get('status')})")

        # 3. List Tasks
        logger.info(f"Listing tasks for project {project_id}...")
        tasks_response = await client.list_tasks(project_id=project_id)
        tasks = tasks_response.get("items", [])
        logger.info(f"Found {len(tasks)} tasks.")
        
        # 4. Analyze Sprint Assignment
        sprint_task_counts = {}
        tasks_with_sprint = 0
        tasks_without_sprint = 0
        
        for task in tasks:
            s_id = task.get("sprint_id")
            if s_id:
                tasks_with_sprint += 1
                sprint_task_counts[s_id] = sprint_task_counts.get(s_id, 0) + 1
            else:
                tasks_without_sprint += 1
                
        logger.info(f"Tasks with sprint_id: {tasks_with_sprint}")
        logger.info(f"Tasks without sprint_id: {tasks_without_sprint}")
        logger.info("Breakdown by Sprint ID:")
        for s_id, count in sprint_task_counts.items():
            # Find sprint name
            s_name = next((s.get("name") for s in sprints if s.get("id") == s_id), "Unknown")
            logger.info(f" - Sprint {s_id} ({s_name}): {count} tasks")

        # 5. Inspect a few tasks that SHOULD be in a sprint (if any)
        # Or just dump the first 5 tasks to see structure
        logger.info("Sample Task Dump (first 3):")
        import json
        for i, task in enumerate(tasks[:3]):
             logger.info(f"Task {i}: {json.dumps(task, indent=2)}")

if __name__ == "__main__":
    asyncio.run(debug_tasks())
