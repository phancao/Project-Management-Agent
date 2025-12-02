#!/usr/bin/env python3
"""
Script to identify which agent is being used in the DeerFlow workflow.

This script:
1. Monitors the stream to identify which agents are called
2. Checks the plan type (research vs PM analysis)
3. Logs agent usage patterns
"""

import asyncio
import json
import sys
from urllib.parse import urljoin

import httpx

BACKEND_URL = "http://localhost:8000"
TEST_PROJECT_ID = "e6890ea6-0c3c-4a83-aa05-41b223df3284:478"
TEST_QUERY = f"Comprehensive project analysis for project {TEST_PROJECT_ID}. Include all analytics: velocity, burndown, CFD, cycle time, work distribution, issue trends, and task statistics."


async def identify_agent_usage(query: str):
    """Identify which agents are being used in the workflow."""
    url = urljoin(BACKEND_URL, "/api/pm/chat/stream")
    
    enhanced_query = f"{query}\n\nproject_id: {TEST_PROJECT_ID}"
    
    payload = {
        "messages": [{"role": "user", "content": enhanced_query}],
        "locale": "en-US",
        "thread_id": "test_agent_identification",
        "auto_accepted_plan": True,
        "enable_background_investigation": True,
        "enable_deep_thinking": False,
        "enable_clarification": False,
        "max_plan_iterations": 1,
        "max_step_num": 10,
    }
    
    print("=" * 80)
    print("AGENT USAGE IDENTIFICATION")
    print("=" * 80)
    print(f"Query: {query}")
    print(f"URL: {url}")
    print("\nMonitoring stream for agent usage...\n")
    
    agents_seen = set()
    plan_content = ""
    tool_calls = []
    agent_sequence = []
    
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
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
                                    
                                    # Track agent usage
                                    agent = data.get("agent") or data.get("name")
                                    if agent:
                                        agents_seen.add(agent)
                                        agent_sequence.append({
                                            "agent": agent,
                                            "event": current_event_type,
                                            "timestamp": data.get("timestamp")
                                        })
                                        print(f"  ✓ Agent: {agent} | Event: {current_event_type}")
                                    
                                    # Track plan content
                                    if current_event_type == "message_chunk" and agent == "planner":
                                        content = data.get("content", "")
                                        plan_content += content
                                    
                                    # Track tool calls
                                    if current_event_type == "tool_calls" and data.get("tool_calls"):
                                        for tc in data.get("tool_calls", []):
                                            tool_calls.append({
                                                "name": tc.get("name"),
                                                "agent": agent,
                                                "args": tc.get("args", {})
                                            })
                                            print(f"  🔧 Tool: {tc.get('name')} | Agent: {agent}")
                                    
                                except json.JSONDecodeError:
                                    pass
                    
    except Exception as e:
        print(f"Error: {e}")
        return
    
    print("\n" + "=" * 80)
    print("ANALYSIS RESULTS")
    print("=" * 80)
    
    print(f"\n📊 Agents Seen: {', '.join(sorted(agents_seen))}")
    print(f"📝 Total Agents: {len(agents_seen)}")
    
    print(f"\n🔄 Agent Sequence:")
    for i, entry in enumerate(agent_sequence[:20], 1):  # Show first 20
        print(f"  {i}. {entry['agent']} ({entry['event']})")
    
    print(f"\n🔧 Tools Called: {len(tool_calls)}")
    tool_names = [tc['name'] for tc in tool_calls]
    unique_tools = set(tool_names)
    print(f"  Unique Tools: {len(unique_tools)}")
    print(f"  Tools: {', '.join(sorted(unique_tools))}")
    
    # Analyze plan type
    print(f"\n📋 Plan Analysis:")
    if plan_content:
        plan_lower = plan_content.lower()
        is_pm_plan = any(keyword in plan_lower for keyword in [
            "pm_query", "pm_agent", "list_tasks", "list_sprints",
            "velocity_chart", "burndown_chart", "project_health"
        ])
        is_research_plan = any(keyword in plan_lower for keyword in [
            "research", "web_search", "investigate", "gather information"
        ])
        
        print(f"  Plan Type Detection:")
        print(f"    - PM Plan: {is_pm_plan}")
        print(f"    - Research Plan: {is_research_plan}")
        
        if is_research_plan and not is_pm_plan:
            print(f"\n  ⚠️  WARNING: Plan is research-focused, not PM-focused!")
            print(f"     This suggests the planner is using 'planner.md' instead of 'pm_planner.md'")
        elif is_pm_plan:
            print(f"\n  ✅ Plan is PM-focused - correct!")
    else:
        print(f"  No plan content captured")
    
    # Check for PM tools
    pm_tools = [
        "list_tasks", "list_sprints", "get_project", "project_health",
        "velocity_chart", "burndown_chart", "sprint_report", "cfd_chart",
        "cycle_time_chart", "work_distribution_chart", "issue_trend_chart"
    ]
    pm_tools_called = [tc for tc in tool_calls if tc['name'] in pm_tools]
    print(f"\n🎯 PM Tools Analysis:")
    print(f"  PM Tools Called: {len(pm_tools_called)}/{len(pm_tools)}")
    if len(pm_tools_called) < len(pm_tools):
        missing = set(pm_tools) - {tc['name'] for tc in pm_tools_called}
        print(f"  Missing PM Tools: {', '.join(sorted(missing))}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    query = TEST_QUERY
    if len(sys.argv) > 1:
        query = sys.argv[1]
    
    asyncio.run(identify_agent_usage(query))

