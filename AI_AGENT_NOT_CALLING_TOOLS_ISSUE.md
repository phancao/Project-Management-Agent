# AI Agent Not Calling Tools - Critical Issue

**Date**: November 27, 2025  
**Status**: 🔴 CRITICAL - AI Agent Not Using MCP Tools

## Problem

The AI agent is **NOT calling any MCP tools** and instead generating reports about "404 errors" and "data retrieval issues" that never actually occurred.

### Evidence

From the logs (session `QYPZd-ldoANgkLOEYYVVx`):

**1. AI's Report Claims**:
```
"Data Retrieval Issues: Efforts to retrieve specific details of Sprint 4 
were met with continuous 404 Not Found errors"
```

**2. Actual Tool Calls**:
```
DEBUG: Processing AIMessageChunk, tool_calls=False, tool_call_chunks=False
(repeated hundreds of times)
```

**Result**: ZERO tool calls were made. The AI fabricated the "404 errors".

## Root Cause

This is the **SAME ISSUE** we identified and temporarily fixed before:
- The AI agent has access to MCP PM tools (26 tools available)
- The AI agent is NOT calling these tools
- Instead, it generates generic reports based on web search results

## Why This is Happening

### Possible Causes:

1. **LLM Not Prompted Correctly**: The agent's prompt doesn't emphasize using PM tools
2. **Tool Descriptions Unclear**: The MCP tools might not have clear enough descriptions
3. **LLM Prefers Web Search**: The LLM finds it easier to search the web than call PM tools
4. **Missing Context**: The agent doesn't know which project/sprint IDs to use

## Previous "Fix" Was Temporary

Previously, we:
- Disabled fake analytics tools in `src/tools/analytics_tools.py`
- This forced the agent to use MCP tools

But the underlying issue remains: **The agent doesn't naturally prefer PM tools over web search**.

## What Should Happen

For a query like "Analyze Sprint 4":

### Expected Flow:
```
1. Planner creates plan with steps:
   - Step 1: Get Sprint 4 details (use list_sprints, get_sprint)
   - Step 2: Get Sprint 4 tasks (use list_tasks)
   - Step 3: Analyze metrics (use sprint_report, burndown_chart)

2. Researcher executes Step 1:
   - Calls list_sprints(project_id="...")
   - Calls get_sprint(sprint_id="...")
   - Gets actual sprint data

3. Coder executes Step 2:
   - Calls list_tasks(sprint_id="...")
   - Gets actual task data

4. Reporter generates report based on REAL data
```

### Actual Flow (Current):
```
1. Planner creates vague plan
2. Researcher searches web for "sprint metrics"
3. Reporter generates generic report about "404 errors"
4. NO PM tools called
```

## Solutions

### Option 1: Improve Prompts (Quick Fix)

Modify the planner and researcher prompts to:
- Explicitly mention PM tools are available
- Provide examples of when to use PM tools
- Emphasize using PM tools BEFORE web search

**Files to modify**:
- `src/prompts/planner.md`
- `src/prompts/researcher.md`

### Option 2: Add Tool Selection Logic (Medium)

Add logic to detect PM-related queries and force PM tool usage:
- If query mentions "sprint", "task", "project" → use PM tools
- Add a pre-processing step to identify the intent
- Route to PM-specific workflow

### Option 3: Create Dedicated PM Agent (Long-term)

Create a specialized PM agent that:
- Only has access to PM tools (no web search)
- Is triggered for PM-related queries
- Has prompts optimized for PM tool usage

## Immediate Action Required

The current situation is:
- ❌ AI agent not using PM tools
- ❌ Generating fake error reports
- ❌ Users getting generic web-based responses
- ❌ MCP server integration not being utilized

**Recommendation**: Implement Option 1 (Improve Prompts) immediately to fix this issue.

## Testing

To verify the fix works:

1. Start a NEW workflow with query: "Analyze Sprint 4 performance"
2. Check logs for tool calls:
   ```bash
   docker logs pm-backend-api 2>&1 | grep "tool_calls=True"
   ```
3. Should see calls to:
   - `list_sprints`
   - `get_sprint`
   - `list_tasks`
   - `sprint_report` or `burndown_chart`

## Related Issues

- This is why step progress isn't showing (no plan with PM tool steps)
- This is why users see generic reports instead of actual data
- This is the core issue preventing the PM MCP integration from working

---

**Priority**: 🔴 CRITICAL  
**Impact**: HIGH - Core functionality not working  
**Effort**: LOW (Option 1) to HIGH (Option 3)  
**Recommendation**: Start with Option 1 immediately

