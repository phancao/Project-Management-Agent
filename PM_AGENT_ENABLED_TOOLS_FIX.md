# PM Agent enabled_tools=None Bug Fix

## Issue Summary

After adding `pm_agent` to the `add_to_agents` list, the PM Agent was still **not receiving any PM tools** from the MCP server. Investigation revealed a critical bug in the MCP tool loading logic.

## Root Cause

The bug was in `src/graph/nodes.py` at line 1003:

```python
if (
    server_config["enabled_tools"]  # ❌ This is False when enabled_tools=None!
    and agent_type in server_config["add_to_agents"]
):
```

### The Problem

In our MCP configuration, `enabled_tools` is set to `None` to indicate "enable all tools":

```python
"pm-server": {
    "enabled_tools": None,  # Enable all available PM tools (55 total)
    "add_to_agents": ["researcher", "coder", "pm_agent"],
}
```

However, in Python:
- `if None:` evaluates to `False`
- So the condition `if server_config["enabled_tools"]` failed
- The MCP server was never added to `mcp_servers`
- No tools were loaded for the PM Agent

## Evidence from Logs

### Session: BMyyjqo6BGa9MAyTEQE0i (Started 06:12:33, after backend restart at 06:11:00)

1. ✅ PM Agent node executed 3 times
2. ✅ PM Agent detected MCP settings: `Server 'pm-server' in mcp_settings: transport=sse, has_url=True`
3. ❌ **Missing**: "Connecting to MCP server" logs
4. ❌ **Missing**: "Retrieved X tools from MCP servers" logs
5. ❌ **Result**: PM Agent had `tool_calls=False` throughout - no tools to call!

### MCP Server Logs

Only health checks - no tool invocations at all.

## The Fix

### Part 1: Check `add_to_agents` First

Changed the condition to check `add_to_agents` first, then handle `enabled_tools` separately:

```python
# Check if this agent should use this MCP server
# enabled_tools can be None (all tools), empty list (no tools), or list of specific tools
if agent_type in server_config["add_to_agents"]:
    enabled_tools_config = server_config["enabled_tools"]
    # Skip if explicitly set to empty list (no tools)
    if enabled_tools_config is not None and len(enabled_tools_config) == 0:
        continue
        
    mcp_servers[server_name] = {
        k: v
        for k, v in server_config.items()
        if k in ("transport", "command", "args", "url", "env", "headers")
    }
    # If enabled_tools is None, we'll enable all tools from this server
    # If it's a list, we'll only enable those specific tools
    if enabled_tools_config is not None:
        for tool_name in enabled_tools_config:
            enabled_tools[tool_name] = server_name
    # If None, we don't populate enabled_tools here - all tools will be added later
```

### Part 2: Enable All Tools When `enabled_tools` is Empty

Updated the tool filtering logic to handle the case where `enabled_tools` dict is empty (meaning all tools should be enabled):

```python
for tool in all_tools:
    # If enabled_tools is empty, enable ALL tools from all connected servers
    # Otherwise, only enable tools that are in the enabled_tools dict
    if not enabled_tools or tool.name in enabled_tools:
        server_name = enabled_tools.get(tool.name, "unknown") if enabled_tools else list(mcp_servers.keys())[0] if mcp_servers else "unknown"
        tool.description = (
            f"Powered by '{server_name}'.\n{tool.description}"
        )
        loaded_tools.append(tool)
        added_count += 1
        # ... logging ...
```

## Behavior After Fix

### `enabled_tools` Configuration Options

1. **`enabled_tools: None`** → Enable ALL tools from this MCP server
2. **`enabled_tools: ["tool1", "tool2"]`** → Enable only specific tools
3. **`enabled_tools: []`** → Enable NO tools (skip this server)

## Files Modified

1. **src/graph/nodes.py** - Fixed MCP tool loading logic

## Testing Required

To verify the fix works:

1. **Start a NEW workflow** (workflows started before 06:15:43 UTC won't have the fix)
2. Ask a PM-related query like:
   - "Analyze Sprint 4 performance"
   - "Show me the burndown chart for Sprint 4"
3. Check backend logs for MCP connection:
   ```bash
   docker logs pm-backend-api --tail 100 | grep "pm_agent.*Connecting to.*MCP"
   docker logs pm-backend-api --tail 100 | grep "pm_agent.*Retrieved.*tools"
   docker logs pm-backend-api --tail 100 | grep "pm_agent.*Added.*MCP tool"
   ```
4. Check MCP server logs for tool invocations:
   ```bash
   docker logs pm-mcp-server --tail 50 | grep -v "GET /health"
   ```

## Timeline

1. **06:11:00** - First fix: Added `pm_agent` to `add_to_agents` list
2. **06:12:33** - User started new workflow, but PM Agent still didn't call tools
3. **06:13:00** - Investigation revealed the `enabled_tools=None` bug
4. **06:15:43** - Second fix: Updated logic to handle `enabled_tools=None`

## Key Learnings

1. **Falsy Values**: Be careful with conditions like `if config_value` when the value can be `None` with special meaning
2. **None vs Empty List**: `None` often means "default/all", while `[]` means "explicitly none"
3. **Multi-Layer Debugging**: 
   - First layer: Is the agent in `add_to_agents`? ✅
   - Second layer: Is the MCP server being connected? ❌ (This was the bug)
   - Third layer: Are tools being called? (Would be next if server connected)

## Related Issues

- `PM_AGENT_TOOL_ACCESS_FIX.md` - First fix (add_to_agents)
- `PM_AGENT_IMPLEMENTATION.md` - Original PM Agent implementation
- `AI_AGENT_NOT_CALLING_TOOLS_ISSUE.md` - Original problem that led to PM Agent

## Status

✅ **Fixed** - Backend restarted at 2025-11-27 06:15:43 UTC

**Next Step**: User needs to start a NEW workflow to test the PM Agent with PM tools properly loaded.

## Commits

1. `3fdc795` - fix: Add pm_agent to MCP server add_to_agents list
2. `b7c02a3` - fix: Handle enabled_tools=None to enable all MCP tools

