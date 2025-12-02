#!/usr/bin/env python3
"""
Test script to verify PM query detection for different analysis types.

This script tests various analysis queries to ensure they're detected as PM queries
and use pm_query step_type instead of research.
"""

import asyncio
import json
import sys
from urllib.parse import urljoin

import httpx

BACKEND_URL = "http://localhost:8000"
TEST_PROJECT_ID = "e6890ea6-0c3c-4a83-aa05-41b223df3284:478"

# Test queries for different analysis types
TEST_QUERIES = [
    # Project analysis
    ("Project Analysis", f"Comprehensive project analysis for project {TEST_PROJECT_ID}"),
    ("Project Status", f"What's the status of project {TEST_PROJECT_ID}?"),
    ("Project Health", f"Check project health for {TEST_PROJECT_ID}"),
    
    # Sprint analysis
    ("Sprint Analysis", f"Analyze sprint 5 in project {TEST_PROJECT_ID}"),
    ("Sprint Performance", f"How did sprint 4 perform in project {TEST_PROJECT_ID}?"),
    ("Sprint Metrics", f"Show sprint metrics for project {TEST_PROJECT_ID}"),
    
    # Task analysis
    ("Task Analysis", f"Analyze tasks in project {TEST_PROJECT_ID}"),
    ("Task Progress", f"Show task progress for project {TEST_PROJECT_ID}"),
    ("Task Statistics", f"Task statistics for project {TEST_PROJECT_ID}"),
    
    # Epic analysis
    ("Epic Analysis", f"Analyze epics in project {TEST_PROJECT_ID}"),
    ("Epic Progress", f"Show epic progress for project {TEST_PROJECT_ID}"),
    
    # Team metrics
    ("Team Performance", f"Team performance for project {TEST_PROJECT_ID}"),
    ("Team Velocity", f"Show team velocity for project {TEST_PROJECT_ID}"),
    
    # Analytics
    ("Velocity Chart", f"Show velocity chart for project {TEST_PROJECT_ID}"),
    ("Burndown Analysis", f"Burndown analysis for sprint 5 in project {TEST_PROJECT_ID}"),
    ("CFD Chart", f"Show CFD chart for project {TEST_PROJECT_ID}"),
    ("Cycle Time", f"Cycle time analysis for project {TEST_PROJECT_ID}"),
    ("Work Distribution", f"Work distribution for project {TEST_PROJECT_ID}"),
    ("Issue Trend", f"Issue trend analysis for project {TEST_PROJECT_ID}"),
    
    # Simple queries
    ("List Tasks", f"List tasks in project {TEST_PROJECT_ID}"),
    ("List Sprints", f"List sprints in project {TEST_PROJECT_ID}"),
    ("My Tasks", "Show me my tasks"),
]


async def test_query(query_name: str, query: str):
    """Test a single query and check if it's detected as PM query."""
    url = urljoin(BACKEND_URL, "/api/pm/chat/stream")
    
    payload = {
        "messages": [{"role": "user", "content": query}],
        "locale": "en-US",
        "thread_id": f"test_{query_name.lower().replace(' ', '_')}",
        "auto_accepted_plan": True,
        "enable_background_investigation": False,
        "enable_deep_thinking": False,
        "enable_clarification": False,
        "max_plan_iterations": 1,
        "max_step_num": 3,
    }
    
    print(f"\n{'='*80}")
    print(f"Testing: {query_name}")
    print(f"Query: {query}")
    print(f"{'='*80}")
    
    plan_content = ""
    agents_seen = set()
    tool_calls = []
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                
                current_event_type = None
                buffer = ""
                
                async for line_bytes in response.aiter_bytes():
                    line = line_bytes.decode('utf-8', errors='ignore')
                    buffer += line
                    
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        if line.startswith("event: "):
                            current_event_type = line[7:].strip()
                        elif line.startswith("data: ") and current_event_type:
                            data_str = line[6:].strip()
                            if data_str and data_str != "null":
                                try:
                                    data = json.loads(data_str)
                                    
                                    agent = data.get("agent") or data.get("name")
                                    if agent:
                                        agents_seen.add(agent)
                                    
                                    if current_event_type == "message_chunk" and agent == "planner":
                                        plan_content += data.get("content", "")
                                    
                                    if current_event_type == "tool_calls" and data.get("tool_calls"):
                                        for tc in data.get("tool_calls", []):
                                            tool_calls.append(tc.get("name"))
                                    
                                except json.JSONDecodeError:
                                    pass
                    
                    # Stop after getting plan (planner message)
                    if plan_content and len(plan_content) > 500:
                        break
                    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Analyze results
    print(f"\n📊 Results:")
    print(f"  Agents: {', '.join(sorted(agents_seen))}")
    print(f"  Tools: {', '.join(tool_calls[:5])}")
    
    # Check plan content
    if plan_content:
        plan_lower = plan_content.lower()
        
        # Check for PM query indicators
        has_pm_query = "pm_query" in plan_lower or '"step_type": "pm_query"' in plan_content
        has_research = "research" in plan_lower and '"step_type": "research"' in plan_content
        has_web_search = "need_search" in plan_lower and '"need_search": true' in plan_content
        
        print(f"\n📋 Plan Analysis:")
        print(f"  Has pm_query: {has_pm_query}")
        print(f"  Has research: {has_research}")
        print(f"  Has web_search: {has_web_search}")
        
        if has_pm_query and not has_research:
            print(f"  ✅ CORRECT: Using PM query (not research)")
            return True
        elif has_research and not has_pm_query:
            print(f"  ❌ WRONG: Using research instead of PM query")
            return False
        else:
            print(f"  ⚠️  UNCLEAR: Mixed or unclear plan type")
            return None
    else:
        print(f"  ⚠️  No plan content captured")
        return None


async def main():
    """Run all test queries."""
    print("="*80)
    print("PM QUERY DETECTION TEST")
    print("="*80)
    print(f"Testing {len(TEST_QUERIES)} different analysis types...")
    
    results = []
    for query_name, query in TEST_QUERIES:
        result = await test_query(query_name, query)
        results.append((query_name, result))
        await asyncio.sleep(1)  # Small delay between tests
    
    # Summary
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    correct = sum(1 for _, r in results if r is True)
    wrong = sum(1 for _, r in results if r is False)
    unclear = sum(1 for _, r in results if r is None)
    
    print(f"\n✅ Correct (PM query): {correct}/{len(results)}")
    print(f"❌ Wrong (Research): {wrong}/{len(results)}")
    print(f"⚠️  Unclear: {unclear}/{len(results)}")
    
    if wrong > 0:
        print(f"\n❌ Queries that incorrectly used research:")
        for name, result in results:
            if result is False:
                print(f"  - {name}")
    
    print(f"\n{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())

