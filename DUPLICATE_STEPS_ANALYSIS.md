# Duplicate Steps Analysis - Why Steps Are Executed Multiple Times

## The Problem

Steps are being executed **3 times** (same 3 steps repeated):
- List Sprints (#1, #4, #7)
- Sprint Report (#2, #5, #8)  
- Burndown Chart (#3, #6, #9)

## Root Cause Analysis

### Issue 1: LangGraph State Conflict (Causing Crash)

**Error:**
```
At key 'retry_count': Can receive only one value per step. Use an Annotated key to handle multiple values.
```

**Cause:**
Both `validator_node` and `reflection_node` are trying to update `retry_count` in the same step:

1. **Validator** (line 2955): Sets `retry_count: 0` when routing to reflector
2. **Reflector** (line 3047): Also sets `retry_count: 0` when routing to planner

When both nodes run in the same step, LangGraph throws an error because you can't have two nodes update the same key.

### Issue 2: Replanning Loop (Causing Duplicate Steps)

**Flow:**
```
1. Planner creates plan with 3 steps (List Sprints, Sprint Report, Burndown Chart)
2. Steps execute → Analyze Sprint 8 (wrong sprint!)
3. Validator validates → FAILS: "Sprint 8 instead of Sprint 10"
4. Reflector replans → Creates NEW plan with same 3 steps
5. Steps execute again → Still analyzes Sprint 8 (same issue!)
6. Validator validates → FAILS again
7. Loop continues...
```

**Why it keeps failing:**
- Validator expects Sprint 10
- Steps keep analyzing Sprint 8
- Replanning doesn't fix the root cause (wrong sprint ID being used)
- Same steps get executed again with same wrong sprint ID

## The Flow Breakdown

### Step Execution Flow:
```
Planner → research_team → pm_agent (Step 1: List Sprints)
  ↓
research_team → pm_agent (Step 2: Sprint Report)  
  ↓
research_team → pm_agent (Step 3: Burndown Chart)
  ↓
research_team → validator (All steps complete)
  ↓
validator → FAILS: "Sprint 8 instead of Sprint 10"
  ↓
validator → reflector (Replan)
  ↓
reflector → planner (Create new plan)
  ↓
planner → research_team → pm_agent (Step 1: List Sprints) ← DUPLICATE!
  ↓
... (cycle repeats)
```

## Why Steps Are Duplicated in UI

The frontend shows all tool calls from all executions:
- **First execution**: Steps #1, #2, #3
- **Second execution** (after replan): Steps #4, #5, #6
- **Third execution** (after replan): Steps #7, #8, #9

All these tool calls are added to the same research block's `activityIds`, so they all appear in the UI.

## Solutions Needed

1. **Fix State Conflict**: Only one node should update `retry_count` per step
2. **Fix Replanning Logic**: Replanning should actually fix the issue (use correct sprint ID)
3. **Prevent Infinite Loops**: Add max replan iterations check (already exists but not working due to state conflict)
4. **Better Validation**: Validator should be less strict or steps should use correct sprint ID from the start


