#!/usr/bin/env python3
"""
Test script for verifying LLM flow routing.

This script tests whether PM queries correctly route to pm_agent instead of coder.
It calls the backend API directly without using the Web UI.

Usage:
    python scripts/test_llm_flow.py
"""

import asyncio
import json
import httpx
import time
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_PROJECT_ID = "40776286-2d26-405a-80a9-5f9231071833:478"  # Default test project

# Test queries to verify routing
TEST_QUERIES = [
    {
        "query": "List all users in the project",
        "expected_agent": "pm_agent",
        "description": "User listing query should route to pm_agent"
    },
    {
        "query": "Show me the team members",
        "expected_agent": "pm_agent", 
        "description": "Team members query should route to pm_agent"
    },
    {
        "query": "What tasks are in the current sprint?",
        "expected_agent": "pm_agent",
        "description": "Sprint tasks query should route to pm_agent"
    },
]


async def test_chat_stream(query: str, project_id: str = TEST_PROJECT_ID):
    """
    Send a chat request and stream the response.
    Returns the full response and agent information.
    """
    url = f"{API_BASE_URL}/api/chat/stream"
    
    payload = {
        "messages": [{"role": "user", "content": query}],
        "thread_id": f"test_{int(time.time())}",
        "project_id": project_id,
        "max_plan_iterations": 1,
        "max_step_num": 3,
        "enable_background_investigation": False,
        "auto_accepted_plan": True,
    }
    
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"Project ID: {project_id}")
    print(f"{'='*60}")
    
    agents_seen = set()
    events = []
    full_response = ""
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    print(f"❌ HTTP Error: {response.status_code}")
                    return None, []
                
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    
                    while "\n\n" in buffer:
                        event_str, buffer = buffer.split("\n\n", 1)
                        
                        if not event_str.strip():
                            continue
                        
                        # Parse event
                        event_type = "message"
                        event_data = None
                        
                        for line in event_str.split("\n"):
                            if line.startswith("event: "):
                                event_type = line[7:]
                            elif line.startswith("data: "):
                                try:
                                    event_data = json.loads(line[6:])
                                except json.JSONDecodeError:
                                    event_data = line[6:]
                        
                        if event_data:
                            events.append({"event": event_type, "data": event_data})
                            
                            # Track agents
                            if isinstance(event_data, dict):
                                agent = event_data.get("agent", "")
                                if agent:
                                    agents_seen.add(agent)
                                    print(f"  [{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Agent: {agent}, Event: {event_type}")
                                
                                # Capture content
                                content = event_data.get("content", "")
                                if content and event_type == "message_chunk":
                                    full_response += content
        
        print(f"\n📋 Agents seen: {list(agents_seen)}")
        return full_response, list(agents_seen)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, []


async def run_tests():
    """Run all test cases and report results."""
    print("\n" + "="*60)
    print("LLM FLOW ROUTING TEST")
    print("="*60)
    print(f"Start time: {datetime.now().isoformat()}")
    print(f"API: {API_BASE_URL}")
    
    results = []
    
    for test in TEST_QUERIES:
        response, agents = await test_chat_stream(test["query"])
        
        # Check if expected agent was used
        passed = test["expected_agent"] in agents or "react_agent" in agents
        
        # Check if CODER was wrongly used
        coder_used = "coder" in agents
        
        result = {
            "query": test["query"],
            "expected": test["expected_agent"],
            "agents_seen": agents,
            "passed": passed and not coder_used,
            "coder_used": coder_used,
        }
        results.append(result)
        
        if result["passed"]:
            print(f"✅ PASSED: {test['description']}")
        else:
            print(f"❌ FAILED: {test['description']}")
            if coder_used:
                print(f"   ⚠️ CODER was wrongly used!")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    print(f"Passed: {passed}/{len(results)}")
    print(f"Failed: {failed}/{len(results)}")
    
    if failed > 0:
        print("\n❌ Some tests failed!")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['query']}")
                print(f"    Agents: {r['agents_seen']}")
                if r["coder_used"]:
                    print(f"    ⚠️ CODER was used instead of pm_agent!")
    else:
        print("\n✅ All tests passed!")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_tests())
