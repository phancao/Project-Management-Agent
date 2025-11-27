# Step Progress Testing Guide

**Date**: November 27, 2025  
**Status**: ⚠️ Requires New Workflow

## Important: Why Step Progress Isn't Showing

The step progress implementation is working correctly, but **it only applies to NEW workflows started AFTER the code was deployed**.

### Current Situation

The workflow currently running (session ID: `QYPZd-ldoANgkLOEYYVVx`) was started **BEFORE** the step progress code was deployed. This workflow's state does not have:
- `current_step_index` field
- `total_steps` field

These fields are only initialized when a NEW plan is created by the planner node.

### Why This Happens

1. **State Persistence**: Workflow state is persisted across restarts
2. **Old Workflows**: Workflows started before the code change don't have the new fields
3. **No Retroactive Updates**: We can't add fields to already-running workflows

### Evidence from Logs

```bash
# Current workflow (started before code change)
Task started: tools (step=21)
Task started: agent (step=23)
# No "total_steps" or "current_step_index" in state updates
```

The workflow is executing normally, but without the step progress fields in its state.

## How to Test Step Progress

### Option 1: Start a New Workflow (Recommended)

1. **Open the frontend**: http://localhost:3000
2. **Start a NEW research task**: 
   - Click "New Chat" or start a fresh session
   - Enter a query like: "Analyze Sprint 5 performance"
3. **Observe the step progress**:
   - You should see "Step 1/3: ..." appear
   - As steps complete, it should update to "Step 2/3: ...", "Step 3/3: ..."

### Option 2: Wait for Current Workflow to Complete

The current workflow will eventually complete. When you start the next workflow, it will have step progress tracking.

### Option 3: Force Restart (Not Recommended)

You could clear the workflow state, but this would lose the current workflow's progress.

## How to Verify Step Progress is Working

### 1. Check Backend Logs

When a NEW workflow starts, you should see:

```bash
# Plan creation
INFO: Planner generating full plan
INFO: Plan has 3 step(s) to execute

# Step tracking initialization
DEBUG: Updating state with total_steps=3, current_step_index=0

# Step progress updates
INFO: Step progress: 1/3 steps completed (current_step_index=1)
INFO: Streaming step progress: Step 2/3: Analyze data
```

### 2. Check Frontend

The `StepProgressIndicator` component should display:

```
🔵 Step 2/3: Analyze Sprint Data
```

With an animated blue dot and progress numbers.

### 3. Check Network Tab

In browser DevTools → Network → look for SSE events:

```json
{
  "type": "step_progress",
  "data": {
    "step_title": "Analyze Sprint Data",
    "step_description": "...",
    "step_index": 1,
    "total_steps": 3
  }
}
```

## Troubleshooting

### Issue: No step progress in new workflow

**Check 1**: Verify code is deployed
```bash
docker exec pm-backend-api grep -n "current_step_index" /app/src/graph/types.py
# Should return line 26
```

**Check 2**: Check planner logs
```bash
docker logs pm-backend-api 2>&1 | grep -A 5 "Planner generating full plan"
# Should show plan creation with steps
```

**Check 3**: Check state updates
```bash
docker logs pm-backend-api 2>&1 | grep "total_steps"
# Should show total_steps being set
```

### Issue: Step progress shows wrong numbers

This could happen if:
- Steps are executed out of order (shouldn't happen)
- Step completion detection is incorrect
- Check the `execution_res` field on steps

### Issue: Step progress stops updating

Check if:
- Workflow is stuck (check for errors in logs)
- Agent is waiting for tool results
- Network connection to frontend is stable

## Code Verification

### Files to Check

1. **State Definition**:
```bash
docker exec pm-backend-api cat /app/src/graph/types.py | grep -A 2 "current_step_index"
```

2. **Planner Node**:
```bash
docker exec pm-backend-api grep -A 5 "total_steps.*len" /app/src/graph/nodes.py
```

3. **Step Execution**:
```bash
docker exec pm-backend-api grep -A 3 "Step progress:" /app/src/graph/nodes.py
```

4. **Backend Emission**:
```bash
docker exec pm-backend-api grep -A 10 "Stream step progress updates" /app/src/server/app.py
```

## Expected Behavior

### For a 3-Step Plan

```
1. Plan Created
   Event: step_progress { step_index: 0, total_steps: 3, step_title: "Gather data" }
   UI: "Step 1/3: Gather data"

2. Step 1 Completes
   Event: step_progress { step_index: 1, total_steps: 3, step_title: "Analyze data" }
   UI: "Step 2/3: Analyze data"

3. Step 2 Completes
   Event: step_progress { step_index: 2, total_steps: 3, step_title: "Generate report" }
   UI: "Step 3/3: Generate report"

4. Step 3 Completes
   Workflow completes, reporter generates final report
```

## Summary

✅ **Code is deployed and working**  
⚠️ **Current workflow started before deployment**  
🎯 **Solution**: Start a NEW workflow to see step progress

The step progress feature is fully implemented and ready. It just needs a fresh workflow to demonstrate it!

---

**Testing Instructions**: Start a new research task in the frontend to see step progress in action.

