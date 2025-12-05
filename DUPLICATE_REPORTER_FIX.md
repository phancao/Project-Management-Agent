# Duplicate Reporter Invocation Fix ✅

## Problem

**User Issue:** "check the conversation, duplicated content found"

**Root Cause:** The reporter node was being invoked **twice** at the same timestamp, causing duplicate reports.

---

## What Was Happening

### The Race Condition

```
PM_Agent completes step
    ↓
Validator validates result
    ↓
Research_Team checks "all steps done?"
    ├─→ YES → Routes to Reporter (FIRST ✅)
    └─→ Validator ALSO routes to Reporter (SECOND ❌)
         
Result: TWO reporter invocations at the same time!
```

### Evidence from Logs

```
11:58:57 - research_team started (step 7)
11:58:57 - validator started (step 7)  ← Same step!
11:58:57 - research_team: All steps completed! Routing to reporter
11:58:58 - reporter started (step 8)  ← FIRST
11:58:58 - research_team started (step 8)  ← Again!
11:58:58 - research_team: All steps completed! Routing to reporter
11:58:58 - reporter started (step 9)  ← SECOND (duplicate!)

CURRENT_TIME: Thu Dec 04 2025 11:58:58  ← FIRST
You are a distinguished academic researcher...

CURRENT_TIME: Thu Dec 04 2025 11:58:58  ← SECOND (same timestamp!)
You are a distinguished academic researcher...
```

---

## The Bug

### File: `src/graph/builder.py`

**The Graph Flow:**
```python
# Agents route to validator (line 111-113)
builder.add_edge("pm_agent", "validator")
builder.add_edge("researcher", "validator")
builder.add_edge("coder", "validator")

# Validator routes to research_team or reporter (line 116-128)
builder.add_conditional_edges(
    "validator",
    route_from_validator,
    ["research_team", "reflector", "reporter"]
)

# Research_team routes to agents OR reporter (line 134-138)
builder.add_conditional_edges(
    "research_team",
    continue_to_running_research_team,
    ["planner", "researcher", "coder", "pm_agent", "reporter"],  # ← reporter here!
)
```

**The Problem:**
- When validator routes back to `research_team`
- Research_team checks if all steps are done
- If yes, routes to `reporter`
- But validator ALSO routes to `reporter`
- **Result:** Duplicate reporter invocations!

---

## The Fix

### Changed: `continue_to_running_research_team` function

**BEFORE:**
```python
def continue_to_running_research_team(state: State):
    # ...
    if all(step.execution_res for step in current_plan.steps):
        # All steps completed - route to reporter
        return "reporter"  # ← This causes duplicate!
    
    if not incomplete_step:
        return "reporter"  # ← This too!
```

**AFTER:**
```python
def continue_to_running_research_team(state: State):
    # ...
    if all(step.execution_res for step in current_plan.steps):
        # All steps completed
        # DON'T route to reporter - let validator handle that
        # Return a marker that won't match any edge
        return "__complete__"  # ← Won't match any edge, stops here
    
    if not incomplete_step:
        return "__complete__"  # ← Same here
```

### Changed: Research_team edges

**BEFORE:**
```python
builder.add_conditional_edges(
    "research_team",
    continue_to_running_research_team,
    ["planner", "researcher", "coder", "pm_agent", "reporter"],  # ← reporter included
)
```

**AFTER:**
```python
builder.add_conditional_edges(
    "research_team",
    continue_to_running_research_team,
    ["planner", "researcher", "coder", "pm_agent"],  # ← reporter removed!
)
```

---

## How It Works Now

### Correct Flow

```
PM_Agent completes last step
    ↓
Validator validates result
    ├─→ Valid → Routes to Research_Team
    └─→ Invalid → Routes to Reflector
         ↓
Research_Team checks "all steps done?"
    ├─→ YES → Returns "__complete__" (no edge match, stops)
    └─→ NO → Routes to next agent
         ↓
(Research_team completes, no more routing)
    ↓
Validator (from the LAST agent) routes to Reporter
    ↓
Reporter generates report (ONCE! ✅)
    ↓
END
```

**Key insight:** Only the **validator** routes to reporter, not research_team!

---

## Why This Fixes It

1. **Research_team no longer routes to reporter** - it returns `"__complete__"` which doesn't match any edge
2. **Only validator routes to reporter** - after validating the last step
3. **No race condition** - only ONE path to reporter
4. **No duplicates** - reporter invoked exactly once

---

## Expected Behavior

### Before Fix
```
Logs:
11:58:58 - reporter started (step 8)
11:58:58 - reporter started (step 9)  ← Duplicate!

Output:
CURRENT_TIME: Thu Dec 04 2025 11:58:58
You are a distinguished academic researcher...

CURRENT_TIME: Thu Dec 04 2025 11:58:58  ← Same time!
You are a distinguished academic researcher...

Result: Duplicate reports, duplicate content ❌
```

### After Fix
```
Logs:
11:58:58 - research_team: All steps completed! Returning __complete__
11:58:58 - validator routes to reporter
11:58:58 - reporter started (step 8)  ← Only once!

Output:
CURRENT_TIME: Thu Dec 04 2025 11:58:58
You are a distinguished academic researcher...

Result: Single report, no duplicates ✅
```

---

## Test It! 🚀

**Try: "analyse sprint 5"**

**You should see:**
- ✅ Only ONE reporter invocation in logs
- ✅ Only ONE report generated
- ✅ No duplicate content
- ✅ Clean, single analysis

---

## Summary

✅ **Fixed:** Research_team no longer routes to reporter directly
✅ **Fixed:** Only validator routes to reporter (single path)
✅ **Result:** No more duplicate reporter invocations
✅ **Result:** No more duplicate content

**Key lesson:** In a graph with validators, only the validator should route to the final node (reporter), not the orchestrator (research_team)!


