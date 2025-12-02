# How to Identify Which Agent is Being Used

## Problem
The system sometimes routes PM analysis queries to the researcher instead of the PM agent, resulting in research plans instead of PM analysis reports.

## How to Identify Agent Usage

### 1. Check the Stream Events

The SSE stream includes `agent` field in events. Monitor for:

**PM Agent Indicators:**
- `agent: "pm_agent"` in tool_call events
- Tools called: `list_tasks`, `list_sprints`, `velocity_chart`, `burndown_chart`, etc.
- Plan contains: `pm_query`, `step_type: "pm_query"`

**Researcher Agent Indicators:**
- `agent: "researcher"` in tool_call events
- Tools called: `web_search`, `local_search_tool`
- Plan contains: `research`, `step_type: "research"`, `need_search: true`

### 2. Check the Plan Content

The planner generates a plan JSON. Check the plan:

**PM Plan (Correct):**
```json
{
  "steps": [
    {
      "step_type": "pm_query",
      "title": "Comprehensive Project Analysis",
      "description": "Call ALL 11 tools: get_project, project_health, list_sprints, list_tasks, velocity_chart, burndown_chart, sprint_report, cfd_chart, cycle_time_chart, work_distribution_chart, issue_trend_chart."
    }
  ]
}
```

**Research Plan (Wrong for PM queries):**
```json
{
  "steps": [
    {
      "step_type": "research",
      "title": "Research Project Analysis",
      "description": "Gather information about the project",
      "need_search": true
    }
  ]
}
```

### 3. Use the Identification Script

Run the identification script:

```bash
python3 scripts/identify_agent_usage.py "Your query here"
```

This will show:
- Which agents are called
- Which tools are used
- Plan type (PM vs Research)
- Missing PM tools

### 4. Check Backend Logs

Look for these log patterns:

**PM Agent Usage:**
```
[PM-CHAT] Using default MCP settings
Agent: pm_agent
Tool: list_tasks
```

**Researcher Usage:**
```
Agent: researcher
Tool: web_search
step_type: research
```

### 5. Check the Planner Prompt Used

The planner node uses `apply_prompt_template("planner", ...)` which uses `planner.md`.

**For PM queries, it should use `pm_planner.md` instead.**

Check `src/graph/nodes.py` line 375-382:
```python
# Currently uses "planner" (planner.md)
messages = apply_prompt_template("planner", state, configurable, state.get("locale", "en-US"))

# Should use "pm_planner" for PM queries
# messages = apply_prompt_template("pm_planner", state, configurable, state.get("locale", "en-US"))
```

## Root Cause

The planner node always uses `"planner"` prompt template (`planner.md`), which is designed for research queries. For PM queries, it should use `"pm_planner"` prompt template (`pm_planner.md`).

## Solution

1. **Detect PM queries in planner node** - Check if query contains project_id or PM-related keywords
2. **Use pm_planner for PM queries** - Switch to `pm_planner.md` when PM query detected
3. **Add logging** - Log which prompt template is being used

## Quick Check Commands

```bash
# Check which agents are in the stream
docker logs project-management-agent-backend-1 2>&1 | grep -E "Agent:|agent:" | tail -20

# Check for PM tools
docker logs project-management-agent-backend-1 2>&1 | grep -E "list_tasks|velocity_chart|burndown_chart" | tail -20

# Check for research tools
docker logs project-management-agent-backend-1 2>&1 | grep -E "web_search|research" | tail -20

# Run identification script
python3 scripts/identify_agent_usage.py
```

