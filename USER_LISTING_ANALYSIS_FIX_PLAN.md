# User Listing Analysis Fix Plan

## Problem

When user asks to "show me all users" or "list users", the system incorrectly triggers a comprehensive project analysis (DeerFlow research) instead of simply listing users.

**User Query**: "show me all users of this project"

**Expected Behavior**: 
- Call `list_users(project_id)` tool
- Display users in a simple table/list format

**Actual Behavior**:
- System creates a comprehensive project analysis plan
- Triggers DeerFlow research workflow
- Generates full project analytics report (Executive Summary, Sprint Overview, Burndown, Velocity, CFD, etc.)
- Only mentions users in passing within the analysis

## Root Cause Analysis

**ACTUAL ROOT CAUSE FOUND:**

The issue is NOT in the prompts or planner - the LLM correctly calls `list_users(project_id)`. The problem is in the **reporter node**:

1. **Simple Query Detection Only Works for React Routes**: In `src/graph/nodes.py` line 1488, simple query detection only runs when `is_from_react` is True
2. **Planner Routes Skip Detection**: When queries go through the planner (not react), `is_from_react` is False, so simple query detection never runs
3. **Reporter Defaults to PROJECT ANALYSIS**: Even when user/resource queries are detected, the reporter defaults to generating comprehensive PROJECT analysis reports (sprints, velocity, burndown, etc.) instead of RESOURCE ALLOCATION analysis (users, workload, task assignments)
4. **Missing Analysis Type Detection**: The reporter doesn't distinguish between:
   - PROJECT ANALYSIS (sprints, velocity, burndown, CFD, cycle time, issue trends)
   - RESOURCE ALLOCATION ANALYSIS (users, workload, task assignments per user)

**Code Location**: `src/graph/nodes.py` lines 1485-1526

**The Fix**: 
1. Remove the `if is_from_react:` gate so simple query detection works for ALL routes
2. Check observations to detect analysis type based on tools called:
   - If `list_users` + workload tools → RESOURCE ALLOCATION analysis
   - If only `list_users` → Simple user list
   - If analytics tools → PROJECT analysis
3. Add instructions for RESOURCE ALLOCATION analysis format (not project analysis)

## Solution

### Phase 1: Update pm_planner.md ✅ COMPLETED (but not the root cause)
1. ✅ Added `list_users` to the available step types list (line 57)
2. ✅ Added Example 7a showing how to handle "list users" queries
3. ✅ Example uses `step_type: "list_users"` with clear description

### Phase 2: Update planner.md ✅ COMPLETED (but not the root cause)
1. ✅ Enhanced simple PM queries list to include more variations: "show me all users" / "list all users" / "show team members" / "show me all users of this project"
2. ✅ Enhanced step description instruction to explicitly state:
   - Do NOT call analytics tools
   - Do NOT perform comprehensive project analysis
   - This is a simple list query - just present data in table/list format
   - DO NOT generate comprehensive analytics sections

### Phase 3: Update pm_agent.md ✅ COMPLETED (but not the root cause)
1. ✅ Added explicit rules to NOT call analytics tools for simple list queries
2. ✅ Added rule to NOT generate comprehensive analysis - just present users in table/list format
3. ✅ Clarified this is a SIMPLE LIST QUERY, not a comprehensive project analysis

### Phase 4: Fix Root Cause in Reporter Node ✅ COMPLETED
1. ✅ Removed `if is_from_react:` gate so simple query detection works for ALL routes (planner and react)
2. ✅ Added observation-based detection: Check what tools were actually called
3. ✅ If only simple list tools (list_users, list_projects, etc.) were called and NO analytics tools, treat as simple query

### Phase 4: Test
1. Test with query: "show me all users of this project"
2. Verify it calls `list_users(project_id)` only
3. Verify it displays users in simple format, not comprehensive analysis

## Files to Modify

1. `src/prompts/pm_planner.md` - Add list_users step type and example
2. `src/prompts/planner.md` - Verify instructions (may need updates)
3. `src/graph/nodes.py` - May need routing adjustments if needed

## Testing Plan

1. **Test Case 1**: "show me all users of this project"
   - Expected: Simple list of users, no analysis
   
2. **Test Case 2**: "list users"
   - Expected: Simple list of users
   
3. **Test Case 3**: "show me all users"
   - Expected: Simple list of users

## Notes

- The `pm_agent.md` prompt already has correct instructions for listing users (lines 138-164)
- The issue is in the planner creating the wrong plan type
- Need to ensure planner creates simple PM query steps, not comprehensive analysis steps

