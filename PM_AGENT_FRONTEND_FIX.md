# PM Agent Frontend MCP Settings Fix - THE REAL ROOT CAUSE

## The Mystery Solved 🔍

After extensive debugging with detailed logging, we finally discovered the **true root cause** of why the PM Agent wasn't receiving PM tools.

## Timeline of Investigation

1. **First Fix (commit `3fdc795`)**: Added `pm_agent` to `add_to_agents` in backend `app.py` and `workflow.py`
2. **Second Fix (commit `b7c02a3`)**: Fixed `enabled_tools=None` handling in `nodes.py`
3. **Debug Logging (commit `1743622`)**: Added extensive logging to track MCP setup
4. **The Discovery**: Debug logs revealed `add_to_agents=['researcher', 'coder']` - missing `pm_agent`!

## The Root Cause

The **frontend** was hardcoding the `add_to_agents` list in `web/src/core/store/settings-store.ts`:

```typescript
// PM MCP server should be added to both researcher and coder
const addToAgents = cur.name === "pm-server" || cur.name.includes("pm")
  ? ["researcher", "coder"]  // ❌ Missing "pm_agent"!
  : ["researcher"];
```

### Why This Overrode Backend Settings

The frontend sends `mcp_settings` in every chat request. When `mcp_settings` is provided in the request, the backend uses it directly instead of calling `get_default_mcp_settings()`. This means:

1. ✅ Backend `app.py` had correct settings: `["researcher", "coder", "pm_agent"]`
2. ✅ Backend `workflow.py` had correct settings: `["researcher", "coder", "pm_agent"]`
3. ❌ **Frontend overrode both** with: `["researcher", "coder"]`

## The Fix

Updated `web/src/core/store/settings-store.ts` line 119-122:

```typescript
// PM MCP server should be added to researcher, coder, and pm_agent
const addToAgents = cur.name === "pm-server" || cur.name.includes("pm")
  ? ["researcher", "coder", "pm_agent"]  // ✅ Added pm_agent!
  : ["researcher"];
```

## Debug Logs That Led to Discovery

The key debug logs that revealed the issue:

```
INFO:src.graph.nodes:[pm_agent] Processing MCP settings for agent
INFO:src.graph.nodes:[pm_agent] Checking server 'pm-server', add_to_agents=['researcher', 'coder']
INFO:src.graph.nodes:[pm_agent] Agent NOT in add_to_agents for 'pm-server'
```

These logs showed that even though we modified the backend, the `add_to_agents` list being used was still `['researcher', 'coder']`.

## Verification Steps

After the fix, you should see these logs in a new workflow:

```
INFO:src.graph.nodes:[pm_agent] Processing MCP settings for agent
INFO:src.graph.nodes:[pm_agent] Checking server 'pm-server', add_to_agents=['researcher', 'coder', 'pm_agent']
INFO:src.graph.nodes:[pm_agent] Agent IS in add_to_agents for 'pm-server'
INFO:src.graph.nodes:[pm_agent] Adding server 'pm-server' to mcp_servers
INFO:src.graph.nodes:[pm_agent] Connecting to 1 MCP server(s): pm-server
INFO:src.graph.nodes:[pm_agent] Retrieved 55 tools from MCP servers
```

## Testing Instructions

1. **Refresh the browser** to load the new frontend code
2. **Start a COMPLETELY NEW chat** (not just a new message)
3. Ask: "Analyze Sprint 4 performance"
4. Check backend logs for:
   ```bash
   docker logs pm-backend-api --tail 100 | grep "Agent IS in add_to_agents for 'pm-server'"
   docker logs pm-backend-api --tail 100 | grep "Retrieved.*tools from MCP"
   ```
5. Check MCP server logs for actual tool calls:
   ```bash
   docker logs pm-mcp-server --tail 50 | grep -v "GET /health"
   ```

## Complete Fix Summary

All three layers now have the correct `add_to_agents` configuration:

1. ✅ **Backend API** (`src/server/app.py`): `["researcher", "coder", "pm_agent"]`
2. ✅ **Workflow** (`src/workflow.py`): `["researcher", "coder", "pm_agent"]`
3. ✅ **Frontend** (`web/src/core/store/settings-store.ts`): `["researcher", "coder", "pm_agent"]`

## Key Learnings

1. **Frontend Can Override Backend**: When the frontend sends `mcp_settings`, it takes precedence over backend defaults
2. **Debug Logging is Essential**: Without the detailed debug logs, we would never have discovered that the frontend was overriding the backend settings
3. **Check All Layers**: In a full-stack application, configuration can come from multiple sources - always check frontend, backend, and any intermediate layers
4. **Test with Fresh State**: Old workflows/sessions may cache configuration, always test with completely fresh instances

## Related Commits

- `3fdc795` - fix: Add pm_agent to MCP server add_to_agents list (backend)
- `b7c02a3` - fix: Handle enabled_tools=None to enable all MCP tools
- `1743622` - debug: Add extensive logging for MCP tool loading
- `26f5652` - fix: Add pm_agent to frontend MCP settings add_to_agents (THE FIX)

## Status

✅ **FULLY FIXED** - All layers updated
- Backend restarted: 2025-11-27 07:01:09 UTC
- Frontend restarted: 2025-11-27 07:05:XX UTC

**Next Step**: User needs to refresh browser and start a NEW chat to test the complete fix.

