#!/usr/bin/env python3
"""
PM Chat Query Test Suite

This test file covers all PM query types to ensure the custom agent with 
tool_choice='required' correctly handles diverse user requests.

Usage:
    # Run all tests (from project root)
    python -m pytest backend/tests/test_pm_queries.py -v
    
    # Run specific test
    python -m pytest backend/tests/test_pm_queries.py::test_list_tasks_in_sprint -v
    
    # Run with curl (manual testing)
    See TEST_CASES below for curl commands
"""

import asyncio
import json
import pytest
import logging
from typing import Dict, Any, List

# Test configuration
PROJECT_ID = "e6890ea6-0c3c-4a83-aa05-41b223df3284:478"  # AutoFlow QA
BASE_URL = "http://localhost:8000"

logger = logging.getLogger(__name__)

# ============================================================================
# TEST CASES DEFINITION
# ============================================================================
# Each test case includes:
# - query: What the user might ask
# - expected_tool: Which PM tool should be called
# - expected_args: Expected tool arguments (partial match)
# - description: What this test validates

TEST_CASES = [
    # -------------------------------------------------------------------------
    # LIST TASKS
    # -------------------------------------------------------------------------
    {
        "id": "list_tasks_simple",
        "query": "list tasks",
        "expected_tool": "list_tasks",
        "expected_args": {},
        "description": "Simple list all tasks request"
    },
    {
        "id": "list_tasks_in_sprint",
        "query": "list tasks in sprint 6",
        "expected_tool": "list_tasks",
        "expected_args": {"sprint_id": "6"},
        "description": "List tasks filtered by sprint number"
    },
    {
        "id": "show_tasks_sprint",
        "query": "show me tasks in Sprint 4",
        "expected_tool": "list_tasks",
        "expected_args": {"sprint_id": "4"},
        "description": "Alternative phrasing for sprint tasks"
    },
    {
        "id": "tasks_for_sprint",
        "query": "what tasks are in sprint 3?",
        "expected_tool": "list_tasks",
        "expected_args": {"sprint_id": "3"},
        "description": "Question format for sprint tasks"
    },
    
    # -------------------------------------------------------------------------
    # LIST SPRINTS
    # -------------------------------------------------------------------------
    {
        "id": "list_sprints_simple",
        "query": "list sprints",
        "expected_tool": "list_sprints",
        "expected_args": {},
        "description": "Simple list all sprints request"
    },
    {
        "id": "show_sprints",
        "query": "show me all sprints",
        "expected_tool": "list_sprints",
        "expected_args": {},
        "description": "Alternative phrasing for sprints"
    },
    {
        "id": "what_sprints",
        "query": "what sprints do we have?",
        "expected_tool": "list_sprints",
        "expected_args": {},
        "description": "Question format for sprints"
    },
    {
        "id": "project_sprints",
        "query": "show sprints for this project",
        "expected_tool": "list_sprints",
        "expected_args": {},
        "description": "Sprints for current project"
    },
    
    # -------------------------------------------------------------------------
    # LIST EPICS
    # -------------------------------------------------------------------------
    {
        "id": "list_epics_simple",
        "query": "list epics",
        "expected_tool": "list_epics",
        "expected_args": {},
        "description": "Simple list all epics request"
    },
    {
        "id": "show_epics",
        "query": "show me all epics",
        "expected_tool": "list_epics",
        "expected_args": {},
        "description": "Alternative phrasing for epics"
    },
    {
        "id": "what_epics",
        "query": "what epics are in this project?",
        "expected_tool": "list_epics",
        "expected_args": {},
        "description": "Question format for epics"
    },
    
    # -------------------------------------------------------------------------
    # LIST USERS / TEAM MEMBERS
    # -------------------------------------------------------------------------
    {
        "id": "list_users_simple",
        "query": "list users",
        "expected_tool": "list_users",
        "expected_args": {},
        "description": "Simple list all users request"
    },
    {
        "id": "show_team",
        "query": "show team members",
        "expected_tool": "list_users",
        "expected_args": {},
        "description": "Team members phrasing"
    },
    {
        "id": "who_is_on_team",
        "query": "who is on the project team?",
        "expected_tool": "list_users",
        "expected_args": {},
        "description": "Question format for team"
    },
    
    # -------------------------------------------------------------------------
    # GET PROJECT DETAILS
    # -------------------------------------------------------------------------
    {
        "id": "project_details",
        "query": "show project details",
        "expected_tool": "get_current_project_details",
        "expected_args": {},
        "description": "Get current project details"
    },
    {
        "id": "project_description",
        "query": "what is the project description?",
        "expected_tool": "get_current_project_details",
        "expected_args": {},
        "description": "Project description request"
    },
    {
        "id": "about_project",
        "query": "tell me about this project",
        "expected_tool": "get_current_project_details",
        "expected_args": {},
        "description": "General project info request"
    },
    
    # -------------------------------------------------------------------------
    # LIST PROJECTS
    # -------------------------------------------------------------------------
    {
        "id": "list_projects_simple",
        "query": "list all projects",
        "expected_tool": "list_projects",
        "expected_args": {},
        "description": "List all available projects"
    },
    {
        "id": "show_projects",
        "query": "show me available projects",
        "expected_tool": "list_projects",
        "expected_args": {},
        "description": "Alternative phrasing for projects"
    },
    
    # -------------------------------------------------------------------------
    # MY TASKS
    # -------------------------------------------------------------------------
    {
        "id": "my_tasks",
        "query": "show my tasks",
        "expected_tool": "list_my_tasks",
        "expected_args": {},
        "description": "List tasks assigned to current user"
    },
    {
        "id": "tasks_assigned_to_me",
        "query": "what tasks are assigned to me?",
        "expected_tool": "list_my_tasks",
        "expected_args": {},
        "description": "Question format for my tasks"
    },
    
    # -------------------------------------------------------------------------
    # GET CURRENT USER
    # -------------------------------------------------------------------------
    {
        "id": "whoami",
        "query": "who am I?",
        "expected_tool": "get_current_user",
        "expected_args": {},
        "description": "Get current authenticated user"
    },
    {
        "id": "my_profile",
        "query": "show my profile",
        "expected_tool": "get_current_user",
        "expected_args": {},
        "description": "Current user profile request"
    },
    
    # -------------------------------------------------------------------------
    # GET SPECIFIC SPRINT
    # -------------------------------------------------------------------------
    {
        "id": "sprint_details",
        "query": "show details for sprint 6",
        "expected_tool": "get_sprint",
        "expected_args": {"sprint_id": "6"},
        "description": "Get specific sprint details"
    },
    {
        "id": "sprint_info",
        "query": "tell me about Sprint 4",
        "expected_tool": "get_sprint",
        "expected_args": {"sprint_id": "4"},
        "description": "Sprint info request"
    },
]

# ============================================================================
# CURL COMMANDS FOR MANUAL TESTING
# ============================================================================
CURL_TEMPLATE = '''
curl -s -X POST {base_url}/api/pm/chat/stream \\
  -H "Content-Type: application/json" \\
  -d '{{"messages":[{{"role":"user","content":"{query}"}}],"project_id":"{project_id}"}}' \\
  --max-time 120
'''

def generate_curl_commands():
    """Generate curl commands for all test cases."""
    commands = []
    for tc in TEST_CASES:
        cmd = CURL_TEMPLATE.format(
            base_url=BASE_URL,
            query=tc["query"],
            project_id=PROJECT_ID
        ).strip()
        commands.append({
            "id": tc["id"],
            "description": tc["description"],
            "expected_tool": tc["expected_tool"],
            "curl": cmd
        })
    return commands


# ============================================================================
# PYTEST FIXTURES & TESTS
# ============================================================================

@pytest.fixture
def project_id():
    return PROJECT_ID


@pytest.fixture
def base_url():
    return BASE_URL


async def send_pm_query(query: str, project_id: str) -> Dict[str, Any]:
    """Send a PM query and parse the response."""
    import aiohttp
    
    url = f"{BASE_URL}/api/pm/chat/stream"
    payload = {
        "messages": [{"role": "user", "content": query}],
        "project_id": project_id
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, timeout=120) as response:
            text = await response.text()
            
            # Parse SSE events
            tool_calls = []
            for line in text.split('\n'):
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if 'tool_calls' in data and data['tool_calls']:
                            tool_calls.extend(data['tool_calls'])
                    except json.JSONDecodeError:
                        pass
            
            return {
                "raw_response": text,
                "tool_calls": tool_calls
            }


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", TEST_CASES, ids=[tc["id"] for tc in TEST_CASES])
async def test_pm_query(test_case: Dict[str, Any], project_id: str):
    """Test that PM queries route to the correct tool."""
    query = test_case["query"]
    expected_tool = test_case["expected_tool"]
    expected_args = test_case["expected_args"]
    
    result = await send_pm_query(query, project_id)
    
    # Verify tool was called
    assert result["tool_calls"], f"No tool calls for query: {query}"
    
    # Find the expected tool call
    tool_found = False
    for tc in result["tool_calls"]:
        if tc.get("name") == expected_tool:
            tool_found = True
            # Verify expected args are present
            actual_args = tc.get("args", {})
            for key, value in expected_args.items():
                assert key in actual_args, f"Missing arg '{key}' for tool {expected_tool}"
                assert actual_args[key] == value, f"Wrong value for arg '{key}': expected {value}, got {actual_args[key]}"
            break
    
    assert tool_found, f"Expected tool '{expected_tool}' not called. Got: {[tc.get('name') for tc in result['tool_calls']]}"


# ============================================================================
# MAIN: Generate test commands
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("PM Query Test Cases - Curl Commands")
    print("=" * 80)
    print()
    
    for cmd in generate_curl_commands():
        print(f"# Test: {cmd['id']}")
        print(f"# Description: {cmd['description']}")
        print(f"# Expected Tool: {cmd['expected_tool']}")
        print(cmd['curl'])
        print()
