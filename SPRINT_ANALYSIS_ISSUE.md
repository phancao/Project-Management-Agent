# Sprint Analysis Failure - Agent Not Calling Tools

## Problem Summary

The agent is generating reports about "missing data" and "unconfigured analytics adapter" instead of actually retrieving sprint data using the available MCP tools.

## Root Cause

**The agent is NOT executing the tools it plans to use.** 

### Evidence:

1. **Agent's Plan** (from conversation):
   - "Use the list_sprints MCP PM tool to retrieve data for sprint 4"
   - "Use the list_my_tasks MCP PM tool with project_id"
   
2. **What Actually Happened**:
   - **ZERO tool calls were executed** (confirmed by checking logs)
   - Agent generated a report about "missing data" without ever calling `list_sprints` or `list_tasks`
   - Agent hallucinated about non-existent tools like `get_sprint_analytics` and `get_burndown_chart`

3. **MCP Server Status**:
   - ✅ MCP server is running and healthy
   - ✅ 55 tools available including `list_sprints`, `list_tasks`, `get_sprint`, etc.
   - ✅ Tools are properly registered and accessible

## Why This Happens

The agent is in "research" mode and appears to be:
1. Planning what tools to use
2. **NOT actually executing those tools**
3. Generating a report based on assumptions about what the data "should" look like
4. Hallucinating about analytics tools that don't exist in the MCP server

This is a **LangGraph workflow issue** - the researcher agent is not properly executing its planned steps.

## Solution

### Immediate Fix: Force Tool Execution

The issue is likely in the LangGraph workflow where the researcher agent plans steps but doesn't execute them. You need to:

1. **Check the researcher agent implementation** in `src/graph/nodes.py`
   - Look for the `researcher` or `research_team` node
   - Verify it's actually calling tools, not just planning to call them

2. **Verify tool availability in agent context**
   - Check that MCP tools are properly loaded into the agent's tool list
   - Verify the agent can see and access `list_sprints` and `list_tasks`

3. **Add explicit tool execution**
   - The agent should execute each step in its plan
   - Each tool call should produce an observation
   - The agent should use those observations to generate the report

### Testing the Fix

After implementing the fix, test with:
```
"List all sprints for project 8eedf4f4-6c0e-4061-bca2-4dc10a118f7a:478"
```

Expected behavior:
- Agent should call `list_sprints` tool
- Should receive actual sprint data including Sprint 4
- Should display the sprint information

### Workaround: Direct API Call

Until the agent workflow is fixed, you can verify the data exists by calling the API directly:

```bash
# List sprints
curl "http://localhost:8000/api/pm/projects/8eedf4f4-6c0e-4061-bca2-4dc10a118f7a:478/sprints"

# List tasks
curl "http://localhost:8000/api/pm/projects/8eedf4f4-6c0e-4061-bca2-4dc10a118f7a:478/tasks"
```

## Technical Details

### Available MCP Tools (55 total)

The MCP server provides these relevant tools:
- `list_sprints` - List all sprints for a project
- `list_tasks` - List all tasks for a project  
- `get_sprint` - Get details of a specific sprint
- `list_my_tasks` - List tasks assigned to current user
- `get_task` - Get details of a specific task

### What the Agent Should Do

1. Call `list_sprints(project_id="8eedf4f4-6c0e-4061-bca2-4dc10a118f7a:478")`
2. Find Sprint 4 in the results
3. Call `list_tasks(project_id="...", sprint_id="Sprint-4-ID")`
4. Analyze the actual task data
5. Generate report based on REAL data, not assumptions

### What the Agent Is Actually Doing

1. Plans to call tools ✅
2. **Skips actually calling them** ❌
3. Generates report about "missing data" ❌
4. Hallucinates about non-existent analytics tools ❌

## Next Steps

1. **Investigate LangGraph workflow** - Why aren't planned tools being executed?
2. **Check agent configuration** - Are MCP tools properly loaded?
3. **Add logging** - Log when tools are called vs. just planned
4. **Test with simple query** - "List all projects" should call `list_projects` tool

The core issue is a **workflow execution problem**, not a data availability problem. The data exists, the tools exist, but the agent isn't using them.
