# Duplicate Steps Fix - State Conflict and Replanning Loop

## The Problem

Steps were being executed **3 times** because:
1. **State conflict** causing crash: Both `validator_node` and `reflection_node` tried to update `retry_count` in the same step
2. **Replanning loop**: Validator fails → Reflector → Planner → Same steps → Validator fails again

## Root Cause

### Issue 1: LangGraph State Conflict
**Error:**
```
At key 'retry_count': Can receive only one value per step. Use an Annotated key to handle multiple values.
```

**Cause:**
- `validator_node` (line 2955) sets `retry_count: 0` when routing to reflector
- `reflection_node` (line 3047) also sets `retry_count: 0` when routing to planner
- When both nodes run in sequence, LangGraph detects a conflict

**Fix:**
- Removed `retry_count: 0` from `validator_node` when routing to reflector
- Let `reflection_node` handle the reset to avoid conflicts

### Issue 2: Replanning Loop
**Flow:**
```
1. Planner creates plan: "Analyze Sprint 10"
2. Steps execute → PM agent analyzes Sprint 8 (wrong!)
3. Validator fails: "Sprint 8 instead of Sprint 10"
4. Reflector replans → Creates new plan with same steps
5. Steps execute again → Still analyzes Sprint 8 (same issue!)
6. Loop continues...
```

**Why it keeps failing:**
- PM agent is not correctly identifying Sprint 10
- It's probably using Sprint 8 (maybe index-based confusion)
- Replanning doesn't fix the root cause
- Same steps get executed again with same wrong sprint

**Fix:**
- Enhanced reflection prompt to explicitly address sprint number mismatches
- Added instructions to look up sprint by NAME/NUMBER, not index
- Added better logging to track replanning iterations

## Changes Made

1. **Fixed state conflict** (`src/graph/nodes.py` line 2951-2958):
   - Removed `retry_count: 0` from validator when routing to reflector
   - Added comment explaining why

2. **Enhanced reflection prompt** (`src/graph/nodes.py` line 3008-3030):
   - Added explicit instructions for sprint number mismatches
   - Emphasizes looking up sprint by name/number, not index
   - Helps planner create better plans that actually fix the issue

3. **Better logging**:
   - Added failure reason and suggested fix logging
   - Tracks replanning iterations more clearly

## Expected Behavior After Fix

1. **No more state conflicts**: Only `reflection_node` updates `retry_count`
2. **Better replanning**: Reflection will suggest looking up sprint by name/number
3. **Fewer duplicate steps**: Replanning should actually fix the issue instead of repeating it

## Testing

Test with: `analyse sprint 10`

**Expected:**
- Steps execute once (or twice if first attempt fails)
- Replanning should fix the sprint ID issue
- No infinite loops
- No state conflict errors


