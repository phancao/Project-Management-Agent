
import asyncio
import os
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp_server.core.tool_context import ToolContext
from mcp_server.tools.analytics.capacity_planning import CapacityPlanningTool
from mcp_server.tools.analytics.burndown import BurndownChartTool
from mcp_server.tools.analytics.velocity import VelocityChartTool

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_analytics")

async def main():
    # Setup DB connection (assuming standard path or env var)
    # Trying to find the correct DB URL from config or environment
    db_path = os.environ.get("DATABASE_URL", "sqlite:///./pm_agent.db")
    engine = create_engine(db_path)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Initialize Context
        # User ID is usually required for improved security/context scopes
        # We'll use a placeholder or try to find a user
        context = ToolContext.from_db_session(db_session=db, user_id="user_test_verify")
        
        # 1. List Projects (using Provider Manager) to find a target
        print("\n--- Listing Projects ---")
        providers = context.provider_manager.get_active_providers()
        if not providers:
            print("No active providers found. Please configure a provider.")
            return

        target_project_id = None
        target_sprint_id = None
        
        for provider_conn in providers:
            print(f"Provider: {provider_conn.name} ({provider_conn.id})")
            provider = context.provider_manager.create_provider_instance(provider_conn)
            try:
                projects = await provider.list_projects()
                for p in projects[:3]: # Limit to first 3
                    print(f"  - Project: {p.name} (ID: {p.id})")
                    # Construct composite ID
                    composite_id = f"{provider_conn.id}:{p.id}"
                    if not target_project_id:
                        target_project_id = composite_id
                        print(f"    [SELECTED TARGET PROJECT: {target_project_id}]")
            except Exception as e:
                print(f"  Error listing projects: {e}")

        if not target_project_id:
            print("Could not find a target project.")
            return

        # 2. Test Capacity Planning Tool
        print(f"\n--- Testing CapacityPlanningTool (Project: {target_project_id}) ---")
        capacity_tool = CapacityPlanningTool(context)
        try:
            capacity_result = await capacity_tool.execute(project_id=target_project_id, weeks=4)
            print("Capacity Chart Result (Summary):")
            print(f"  Title: {capacity_result.get('title')}")
            print(f"  Series Count: {len(capacity_result.get('series', []))}")
            for series in capacity_result.get('series', []):
                print(f"    - Series: {series['name']} (Type: {series.get('type')}) -> {len(series.get('data', []))} points")
            
        except Exception as e:
            print(f"ERROR running CapacityPlanningTool: {e}")
            import traceback
            traceback.print_exc()

        # 3. Test Velocity Tool
        print(f"\n--- Testing VelocityChartTool (Project: {target_project_id}) ---")
        velocity_tool = VelocityChartTool(context)
        try:
            velocity_result = await velocity_tool.execute(project_id=target_project_id, num_sprints=3)
            print("Velocity Chart Result (Summary):")
            print(f"  Title: {velocity_result.get('title')}")
            # Identify trend
            meta = velocity_result.get('metadata', {})
            print(f"  Trend: {meta.get('trend')}")
            print(f"  Average Velocity: {meta.get('average_velocity')}")
        except Exception as e:
            print(f"ERROR running VelocityChartTool: {e}")

        # 4. Test Burndown Tool
        # We need a sprint ID for this usually, but it defaults to current
        print(f"\n--- Testing BurndownChartTool (Project: {target_project_id}) ---")
        burndown_tool = BurndownChartTool(context)
        try:
            burndown_result = await burndown_tool.execute(project_id=target_project_id)
            print("Burndown Chart Result (Summary):")
            print(f"  Title: {burndown_result.get('title')}")
            meta = burndown_result.get('metadata', {})
            print(f"  Remaining Points: {meta.get('remaining_points')}")
            print(f"  Sprint Status: {meta.get('sprint_status')}")
        except Exception as e:
            print(f"ERROR running BurndownChartTool: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
