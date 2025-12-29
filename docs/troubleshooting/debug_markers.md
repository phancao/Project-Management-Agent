# Debug Log Markers Reference

## Quick Lookup by Log Prefix

| Log Prefix | Component | File | When to Read |
|------------|-----------|------|--------------|
| `[COORDINATOR]` | Entry point & routing | `nodes.py` | Query routing issues |
| `[PM-AGENT]` | PM tool execution | `nodes.py` | Tool not called, wrong results |
| `[PLANNER]` | Multi-step planning | `nodes.py` | Complex query handling |
| `[VALIDATOR]` | Step validation | `nodes.py` | Step completion issues |
| `[REPORTER]` | Report generation | `nodes.py` | Output formatting issues |
| `[REFLECTION]` | Plan reflection | `nodes.py` | Replanning issues |
| `[PM-TOOLS]` | Tool execution | `pm_tools.py` | Tool method errors |
| `[ERROR]` | Errors | various | Any error occurred |

---

## Log Format Standard

All logs follow this format:
```
[{timestamp}] [PREFIX] Message: details
```

Example:
```
[11:25:34.123] [COORDINATOR] ENTER: Processing user query
[11:25:34.456] [COORDINATOR] Intent: PM detected, routing to PM-AGENT
[11:25:34.789] [PM-AGENT] ENTER: Executing tool list_users
[11:25:35.012] [PM-TOOLS] list_users: Found 5 users
[11:25:35.345] [REPORTER] Generating final report
```

---

## Architecture Docs

| Prefix | Documentation |
|--------|---------------|
| `[COORDINATOR]` | [01_coordinator.md](../architecture/01_coordinator.md) |
| `[PM-AGENT]` | [03_react_agent.md](../architecture/03_react_agent.md) |
| `[PLANNER]` | [04_planner.md](../architecture/04_planner.md) |
| `[REPORTER]` | [05_reporter.md](../architecture/05_reporter.md) |

## Troubleshooting Docs

| Issue | Documentation |
|-------|---------------|
| Routing | [routing_issues.md](routing_issues.md) |
| Tool errors | [tool_errors.md](tool_errors.md) |
| Streaming | [streaming_issues.md](streaming_issues.md) |
