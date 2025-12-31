#!/usr/bin/env python3
"""
Test script for refactored MCP tools.
Tests all V2 tools to ensure they work correctly.
"""

import asyncio
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from mcp_server.server import PMMCPServer
from mcp_server.config import get_config


async def test_tools():
    """Test all refactored tools."""
    print("=" * 80)
    print("Testing Refactored MCP Tools")
    print("=" * 80)
    
    # Initialize MCP server
    config = get_config()
    mcp_server = PMMCPServer(config)
    
    # Initialize PM Handler
    print("\n[1/8] Initializing PM Handler...")
    try:
        await mcp_server._initialize_pm_handler()
        print("✅ PM Handler initialized successfully")
        print(f"   Active providers: {len(mcp_server.pm_handler.providers) if mcp_server.pm_handler else 0}")
    except Exception as e:
        print(f"❌ Failed to initialize PM Handler: {e}")
        return False
    
    # Initialize Tool Context
    print("\n[2/8] Initializing Tool Context...")
    try:
        mcp_server._initialize_tool_context()
        print("✅ Tool Context initialized successfully")
        print(f"   Provider Manager: {mcp_server.tool_context.provider_manager is not None}")
        print(f"   Analytics Manager: {mcp_server.tool_context.analytics_manager is not None}")
    except Exception as e:
        print(f"❌ Failed to initialize Tool Context: {e}")
        return False
    
    # Register tools
    print("\n[3/8] Registering tools...")
    try:
        mcp_server._register_all_tools()
        print(f"✅ Tools registered successfully")
        print(f"   Total tools: {len(mcp_server._tool_names)}")
        print(f"   Tool functions: {len(mcp_server._tool_functions)}")
    except Exception as e:
        print(f"❌ Failed to register tools: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test list_providers
    print("\n[4/8] Testing list_providers...")
    try:
        list_providers_func = mcp_server._tool_functions.get("list_providers")
        if not list_providers_func:
            print("❌ list_providers function not found")
            return False
        
        result = await list_providers_func()
        print(f"✅ list_providers executed successfully")
        print(f"   Result type: {type(result)}")
        print(f"   Result length: {len(result) if isinstance(result, (list, str)) else 'N/A'}")
        
        # Parse result to get provider info
        if isinstance(result, str):
            import json
            providers = json.loads(result)
            if providers:
                provider_id = providers[0].get('id')
                print(f"   First provider ID: {provider_id}")
            else:
                print("   No providers found")
                return False
        else:
            print(f"   Unexpected result type: {type(result)}")
            return False
    except Exception as e:
        print(f"❌ list_providers failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test list_projects (projects_v2)
    print("\n[5/8] Testing list_projects (projects_v2)...")
    try:
        list_projects_func = mcp_server._tool_functions.get("list_projects")
        if not list_projects_func:
            print("❌ list_projects function not found")
            return False
        
        result = await list_projects_func()
        print(f"✅ list_projects executed successfully")
        print(f"   Result type: {type(result)}")
        if isinstance(result, str):
            import json
            projects = json.loads(result)
            print(f"   Projects count: {len(projects)}")
            if projects:
                project_id = projects[0].get('id')
                print(f"   First project ID: {project_id}")
            else:
                print("   No projects found")
        else:
            print(f"   Result: {result[:200] if len(str(result)) > 200 else result}")
    except Exception as e:
        print(f"❌ list_projects failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test get_project (projects_v2)
    print("\n[6/8] Testing get_project (projects_v2)...")
    try:
        get_project_func = mcp_server._tool_functions.get("get_project")
        if not get_project_func:
            print("❌ get_project function not found")
            return False
        
        # Use the project_id from list_projects
        if projects and len(projects) > 0:
            project_id = projects[0].get('id')
            result = await get_project_func(project_id=project_id)
            print(f"✅ get_project executed successfully")
            print(f"   Result type: {type(result)}")
            if isinstance(result, str):
                import json
                project = json.loads(result)
                print(f"   Project name: {project.get('name', 'N/A')}")
                print(f"   Project key: {project.get('key', 'N/A')}")
        else:
            print("⚠️  Skipping get_project test (no projects available)")
    except Exception as e:
        print(f"❌ get_project failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test list_tasks (tasks_v2)
    print("\n[7/8] Testing list_tasks (tasks_v2)...")
    try:
        list_tasks_func = mcp_server._tool_functions.get("list_tasks")
        if not list_tasks_func:
            print("❌ list_tasks function not found")
            return False
        
        # Use the project_id from list_projects
        if projects and len(projects) > 0:
            project_id = projects[0].get('id')
            result = await list_tasks_func(project_id=project_id, limit=5)
            print(f"✅ list_tasks executed successfully")
            print(f"   Result type: {type(result)}")
            if isinstance(result, str):
                import json
                tasks = json.loads(result)
                print(f"   Tasks count: {len(tasks)}")
                if tasks:
                    print(f"   First task ID: {tasks[0].get('id', 'N/A')}")
                    print(f"   First task subject: {tasks[0].get('subject', 'N/A')}")
        else:
            print("⚠️  Skipping list_tasks test (no projects available)")
    except Exception as e:
        print(f"❌ list_tasks failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test list_sprints (sprints_v2)
    print("\n[8/8] Testing list_sprints (sprints_v2)...")
    try:
        list_sprints_func = mcp_server._tool_functions.get("list_sprints")
        if not list_sprints_func:
            print("❌ list_sprints function not found")
            return False
        
        # Use the project_id from list_projects
        if projects and len(projects) > 0:
            project_id = projects[0].get('id')
            result = await list_sprints_func(project_id=project_id)
            print(f"✅ list_sprints executed successfully")
            print(f"   Result type: {type(result)}")
            if isinstance(result, str):
                import json
                sprints = json.loads(result)
                print(f"   Sprints count: {len(sprints)}")
                if sprints:
                    print(f"   First sprint ID: {sprints[0].get('id', 'N/A')}")
                    print(f"   First sprint name: {sprints[0].get('name', 'N/A')}")
        else:
            print("⚠️  Skipping list_sprints test (no projects available)")
    except Exception as e:
        print(f"❌ list_sprints failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 80)
    print("✅ All tests passed!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_tools())
    sys.exit(0 if success else 1)

