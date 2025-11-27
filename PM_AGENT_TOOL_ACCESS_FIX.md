# PM Agent Tool Access Fix

## Issue Discovered

After implementing the dedicated PM Agent, we discovered that it was **not calling any PM tools** despite being designed to do so. The PM Agent node was executing, but the MCP server logs showed no tool invocations.

## Root Cause

The PM Agent was not receiving PM tools because it was **not included in the `add_to_agents` list** for the PM MCP server configuration.

### Code Location

In both `src/workflow.py` and `src/server/app.py`, the PM server configuration had:

```python
"pm-server": {
    "transport": "sse",
    "url": "http://pm_mcp_server:8080/sse",
    "headers": {
        "X-MCP-API-Key": os.getenv("PM_MCP_API_KEY", "...")
    },
    "enabled_tools": None,  # Enable all available PM tools
    "add_to_agents": ["researcher", "coder"],  # ❌ pm_agent missing!
}
```

The `add_to_agents` list controls which agents receive tools from a particular MCP server. Since `"pm_agent"` was not in this list, the PM Agent was not getting any PM tools loaded, even though it was designed to use them exclusively.

## The Fix

Added `"pm_agent"` to the `add_to_agents` list in both locations:

```python
"add_to_agents": ["researcher", "coder", "pm_agent"],  # ✅ pm_agent added!
```

### Files Modified

1. **src/workflow.py** (2 occurrences - lines 95 and 248)
2. **src/server/app.py** (1 occurrence - line 163)

## Verification

After the fix:
1. Backend API restarted successfully
2. New workflows will now load PM tools for the PM Agent
3. The PM Agent will be able to call tools like:
   - `list_sprints`
   - `get_sprint`
   - `sprint_report`
   - `burndown_chart`
   - `velocity_chart`
   - And all other PM tools (55 total)

## Testing Required

To verify the fix works:

1. **Start a NEW workflow** in the frontend (old workflows won't have the fix)
2. Ask a PM-related query like:
   - "Analyze Sprint 4 performance"
   - "Show me the burndown chart for Sprint 4"
   - "What's the velocity trend for the last 3 sprints?"
3. Check the MCP server logs for tool invocations:
   ```bash
   docker logs pm-mcp-server --tail 50 | grep -E "list_sprints|get_sprint|sprint_report"
   ```
4. Check the backend logs to see PM Agent activity:
   ```bash
   docker logs pm-backend-api --tail 100 | grep "pm_agent"
   ```

## Key Learnings

1. **MCP Tool Access Control**: The `add_to_agents` list is crucial for controlling which agents can access which MCP tools.
2. **Agent-Specific Configuration**: When adding a new agent type, remember to update all MCP server configurations that the agent should have access to.
3. **Verification Strategy**: Always check both the agent node execution AND the MCP server logs to verify tool calls are actually happening.

## Related Files

- Implementation: `src/graph/nodes.py` (pm_agent_node)
- Prompt: `src/prompts/pm_agent.md`
- Configuration: `src/config/agents.py`
- Graph: `src/graph/builder.py`
- Planning: `src/prompts/planner_model.py` (PM_QUERY step type)

## Status

✅ **Fixed** - Backend restarted at 2025-11-27 06:11:00 UTC

**Next Step**: User needs to start a NEW workflow to test the PM Agent with PM tools enabled.

