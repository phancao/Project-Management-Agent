# ReAct Agent (PM Tools)

**Log Prefix:** `[PM-AGENT]`  
**File:** `backend/graph/nodes.py` → `react_agent_node()`

## Purpose
Executes PM tool calls using ReAct pattern. Main workhorse for PM queries.

## Flow

```
react_agent_node()
     ↓
run_pm_agent()
     ↓
LLMDrivenPMAgent._act()
     ↓
Tool Execution (list_sprints, list_users, etc.)
     ↓
Return results to reporter
```

## Available Tools

| Tool | Purpose |
|------|---------|
| `get_current_project` | Get selected project from UI |
| `list_projects` | List all projects |
| `list_sprints` | List project sprints |
| `list_tasks` | List tasks in project/sprint |
| `list_users` | List project members |
| `list_epics` | List project epics |
| `get_task` | Get task details |
| `get_sprint` | Get sprint details |

## Debug Logs

| Log Pattern | Meaning |
|-------------|---------|
| `[PM-AGENT] 📝 User query:` | Query received |
| `[PM-AGENT] 📝 Project ID:` | Project context |
| `[PM-AGENT] Set global project context` | Project context set for tools |
| `[PM-AGENT] Tool executed:` | Tool completed |

## Common Issues

### Tool not called
- **Symptom:** Agent responds without data
- **Check:** Is tool in available tools list?
- **Fix:** Verify `get_pm_tools()` includes the tool

### Wrong project context
- **Symptom:** Empty results or wrong data
- **Check:** `[PM-AGENT] Project ID:` log
- **Fix:** Ensure `set_current_project_id()` is called

## See Also
- [pm_tools.md](../components/pm_tools.md) - Tool implementation details
- [01_coordinator.md](01_coordinator.md) - How queries reach react_agent
