# Planner Node

**Log Prefix:** `[PLANNER]`  
**File:** `backend/graph/nodes.py` → `planner_node()`

## Purpose
Handles complex queries that require multi-step research and analysis.

## When Used
- User escalates from ReAct ("need more detail")
- Complex analysis requiring multiple tools
- Research queries needing investigation

## Flow

```
react_agent (escalation)
     ↓
planner_node
     ↓
Creates Plan with Steps
     ↓
research_team_node
     ↓
Execute each step (pm_agent, researcher, coder)
     ↓
reporter
```

## Debug Logs

| Log Pattern | Meaning |
|-------------|---------|
| `[PLANNER] 💉 Injected project context` | Project ID added to plan |
| `[PLANNER] Creating plan for:` | Planning started |
| `[PLANNER] Plan created:` | Steps generated |

## Plan Structure

```python
Plan(
    title="Sprint Analysis",
    thought="Need to analyze sprint performance...",
    steps=[
        Step(type=PM_QUERY, title="Get sprints", ...),
        Step(type=PM_QUERY, title="Get tasks", ...),
        Step(type=PROCESSING, title="Calculate metrics", ...),
    ]
)
```

## Common Issues

### Infinite loop
- **Symptom:** Steps keep executing
- **Check:** `execution_res` on each step
- **Fix:** Ensure validator routes to reporter when done

## See Also
- [05_reporter.md](05_reporter.md) - Final output generation
