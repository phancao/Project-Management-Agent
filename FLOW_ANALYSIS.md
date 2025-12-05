# Flow Analysis: Simple vs Full Analytics

## Your Query: "analyse sprint 10"

Based on the logs, here's what happened:

### Flow Path:
1. **Coordinator** → Routed to **ReAct agent** (fast path)
   - Log: `[COORDINATOR] ⚡ ADAPTIVE ROUTING - Using ReAct fast path (has web_search tool)`
   
2. **ReAct agent** → Failed (too many iterations) → Escalated to **Planner**
   - Log: `[REACT-AGENT] ⬆️ Too many iterations - escalating to planner`
   - Reason: ReAct agent had issues with tool calling (wrong tool names, format errors)
   
3. **Planner** → Created plan → **Full Pipeline**
   - Plan: "Sprint 10 Performance Analysis"
   - Steps: PM tools only (list_sprints, sprint_report, burndown_chart)
   
4. **Full Pipeline Execution**:
   - research_team → pm_agent → validator → reporter
   - No web search used
   - No researcher node used

## Answer:

**This is a FULL ANALYTICS flow (planner-based), but it's a SIMPLE analysis (PM tools only, no web search).**

### Breakdown:

| Aspect | Value |
|--------|-------|
| **Flow Type** | Full Pipeline (Planner-based) |
| **Analysis Type** | Simple (PM tools only) |
| **Web Search** | ❌ Not used |
| **Researcher Node** | ❌ Not used |
| **PM Agent** | ✅ Used (executed plan steps) |
| **Validator** | ✅ Used (validated steps) |
| **Reporter** | ✅ Used (generated final report) |

### Why Full Pipeline?

- ReAct agent failed (too many iterations)
- System automatically escalated to full pipeline
- Full pipeline = Planner → Research Team → Validator → Reporter

### Why Simple Analysis?

- Plan only includes PM tools (list_sprints, sprint_report, burndown_chart)
- No web search needed (sprint data is internal)
- No external research required
- Just retrieving and analyzing sprint data from PM system

### When Would It Use Web Search?

Web search would be used if:
- User asks about external concepts (e.g., "best practices for sprint planning")
- Plan includes research steps (StepType.RESEARCH)
- Researcher node is invoked
- ReAct agent uses web_search tool for background investigation

In your case, "analyse sprint 10" only needs internal PM data, so no web search is required.


