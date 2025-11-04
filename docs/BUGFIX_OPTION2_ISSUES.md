# Bug Fixes for Option 2 Implementation

## Issues Fixed

### Issue 1: List tasks only shows OpenProject, not JIRA

**Problem:**
When asking "list my tasks", the system only listed tasks from OpenProject, not from JIRA.

**Root Cause:**
1. The `list_my_tasks` tool was missing from PM tools - agents couldn't call it
2. PM handler was initialized in single-provider mode, so only one provider was queried

**Solution:**
1. **Added `list_my_tasks` tool** to `src/tools/pm_tools.py`:
   - Calls `handler.list_my_tasks()` which handles multi-provider mode
   - Queries all active providers (OpenProject, JIRA, ClickUp)
   
2. **Changed PM handler initialization** in `src/conversation/flow_manager.py`:
   - Now uses `PMHandler.from_db_session(db_session)` for multi-provider mode
   - Queries all active providers from the database

**Files Changed:**
- `src/tools/pm_tools.py`: Added `list_my_tasks` tool and included it in `get_pm_tools()`
- `src/conversation/flow_manager.py`: Changed PM handler initialization to multi-provider mode

---

### Issue 2: Research query error - "Project with ID not found"

**Problem:**
When asking "Research sprint planning best practices", the system returned an error:
```
❌ Research Sprint Planning Best Practices
Project with ID 77d99cdd-96f5-4113-82f3-4e408c9e678e not found.
```

**Root Cause:**
The `/api/pm/chat/stream` endpoint in `src/server/app.py` was calling `generate_pm_plan()` which tried to access a project from the database. For research queries that don't involve a specific project, this caused a "Project not found" error.

**Solution:**
Modified the API endpoint to skip PM plan generation and route all queries directly to DeerFlow (Option 2 approach):

1. **Skip PM plan generation**: Removed the call to `generate_pm_plan()` 
2. **Always route to DeerFlow**: Set `needs_research = True` for all queries
3. **Use original message**: Use the original user message instead of trying to extract project information

**Files Changed:**
- `src/server/app.py`: 
  - Removed PM plan generation step in `/api/pm/chat/stream` endpoint
  - Changed to always route to DeerFlow
  - Simplified research query to use original user message

---

## Testing

### Test Issue 1 Fix:
1. Ensure both OpenProject and JIRA are configured as active providers in the database
2. Ask: `"List my tasks"`
3. **Expected**: Tasks from both OpenProject and JIRA should be listed

### Test Issue 2 Fix:
1. Ask: `"Research sprint planning best practices"`
2. **Expected**: Query routes to DeerFlow, agents perform research, no project ID errors

---

## Impact

- ✅ **PM tools now query all providers**: Tasks, projects, sprints, epics from all configured providers are accessible
- ✅ **`list_my_tasks` tool available**: Agents can now call this tool to list user's tasks
- ✅ **Research queries work correctly**: No more project ID errors for research queries
- ✅ **Option 2 fully functional**: All queries route to DeerFlow agents as intended

---

## Related Files

- `src/conversation/flow_manager.py`: PM handler initialization
- `src/server/pm_handler.py`: Multi-provider aggregation logic
- `src/tools/pm_tools.py`: PM tools including new `list_my_tasks` tool
- `src/server/app.py`: API endpoint for PM chat streaming (`/api/pm/chat/stream`)

---

**Status**: ✅ **FIXED**

Both issues are resolved. The system now:
1. Has the `list_my_tasks` tool available for agents
2. Queries all active PM providers when listing tasks/projects
3. Routes all queries to DeerFlow without trying to access projects first
