# PM Agent Not Being Used - Analysis

**Date**: November 27, 2025  
**Status**: 🔴 PM Agent Implemented But Not Being Used

## Problem

The PM Agent has been successfully implemented and deployed, but the planner is **NOT creating PM_QUERY steps** for PM analysis queries like "analyse sprint 4".

## Evidence

### Code is Deployed ✅
```bash
# PM Agent prompt exists
-rw-r--r-- 1 root root 5881 Nov 27 05:21 /app/src/prompts/pm_agent.md

# PM_QUERY step type exists
PM_QUERY = "pm_query"  # Project Management query - uses PM agent with PM tools only

# Planner prompt has Complex PM Query section
## Complex PM Analysis Queries
**CRITICAL**: For queries that require analyzing PM data...
```

### User Query
```
"analyse sprint 4"
project_id: d7e300c6-d6c0-4c08-bc8d-e41967458d86:478
```

### What Should Happen
Planner should create a plan with `step_type: "pm_query"` steps:
```json
{
  "steps": [
    {
      "step_type": "pm_query",
      "title": "Retrieve Sprint 4 Details",
      ...
    }
  ]
}
```

### What Actually Happened
- Planner created steps with `step_type: "processing"` (not "pm_query")
- Workflow routed to `coder` agent (not `pm_agent`)
- Coder agent doesn't have proper PM tools access
- Result: "404 errors" and "inaccessible resources"

## Root Cause

The LLM (planner) is **not recognizing** "analyse sprint 4" as a Complex PM Query that should use PM_QUERY steps.

### Possible Reasons:

1. **Prompt Position**: The "Complex PM Analysis Queries" section might be too far down in the prompt
2. **Prompt Emphasis**: Not enough emphasis on when to use PM_QUERY vs PROCESSING
3. **LLM Confusion**: LLM might think "processing" is appropriate for PM data
4. **Context Length**: The planner prompt is very long (~370 lines), LLM might miss the PM_QUERY section

## Solutions

### Option A: Move PM Query Section Higher (Quick Fix)

Move the "Complex PM Analysis Queries" section to the TOP of the planner prompt, right after the title, before "Simple PM Data Queries".

**Rationale**: LLMs pay more attention to content at the beginning of prompts.

### Option B: Add Explicit Step Type Selection (Medium)

Add a decision tree in the planner prompt:
```
Before creating steps, determine the step_type:
- If query is "analyze/analyse [PM entity]" → use "pm_query"
- If query is "list/show [PM entity]" → use "processing"  
- If query requires web research → use "research"
```

### Option C: Simplify Planner Prompt (Long-term)

The planner prompt is 370+ lines. Break it into:
- Core planning logic
- PM query handling (separate section)
- Research query handling (separate section)

### Option D: Force PM_QUERY for Sprint Analysis (Immediate)

Add explicit rule at the top of planner prompt:
```
**CRITICAL RULE**: If user query contains:
- "analyze sprint" / "analyse sprint"
- "sprint [number] analysis"
- "sprint [number] performance"
→ You MUST use step_type: "pm_query" (NOT "processing")
```

## Recommended Approach

Implement **Option D** (immediate) + **Option A** (quick fix):

1. Add explicit rule for sprint analysis at the TOP
2. Move Complex PM Query section higher up
3. Test with "analyse sprint 4" query

## Implementation

### 1. Add Critical Rule at Top of Planner Prompt

Insert after the title, before everything else:

```markdown
# Planner

**CRITICAL RULE - PM QUERY DETECTION**:
If the user query contains ANY of these patterns:
- "analyze sprint" / "analyse sprint" / "sprint analysis"
- "sprint [number]" / "sprint [name]"
- "project status" / "project performance"
- "team performance" / "team velocity"
- "task completion" / "task progress"
- "epic progress" / "epic status"

You MUST create steps with `step_type: "pm_query"` (NOT "processing" or "research").

Example:
- Query: "analyse sprint 4"
- Step type: "pm_query" ✅
- Step type: "processing" ❌
```

### 2. Move Complex PM Section Higher

Move the "Complex PM Analysis Queries" section to line 15 (right after the critical rule).

## Testing

After implementing the fix:

1. Restart backend: `docker restart pm-backend-api`
2. Start NEW workflow with: "analyse sprint 4"
3. Check logs for:
   ```bash
   docker logs pm-backend-api 2>&1 | grep "pm_query\|PM_QUERY"
   ```
4. Should see:
   - Planner creating PM_QUERY steps
   - Workflow routing to pm_agent
   - PM Agent calling PM tools

## Current Workaround

None - the PM Agent exists but isn't being triggered.

## Impact

- 🔴 **HIGH**: PM Agent not being used despite being implemented
- 🔴 **HIGH**: Users still getting fake "404 errors"
- 🔴 **HIGH**: No real PM data in responses

---

**Priority**: 🔴 CRITICAL  
**Next Step**: Implement Option D + Option A immediately

