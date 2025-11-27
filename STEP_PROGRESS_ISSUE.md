# Step Progress Streaming Issue

**Date**: November 27, 2025  
**Status**: ⚠️ Issue Identified

## Problem

The AI agent workflow is not streaming step progress updates to the frontend. Users only see one step progress indicator at the beginning, but don't see updates as the workflow progresses through different steps.

## Root Cause

The `step_progress` events are only emitted when `current_plan` appears in `node_update`, which only happens **once** when the plan is first created by the planner/human_feedback node.

### Evidence from Logs

```
INFO: Streaming plan update from human_feedback: 3 steps
INFO: Streaming step progress: Step 1/3: Gather Sprint 4 Objectives and Tasks
```

Only **ONE** step_progress event was emitted for the entire workflow, even though the workflow executed through multiple agents (coordinator, planner, researcher, coder, reporter).

## Current Implementation

### Backend (`src/server/app.py`)

The step_progress emission code (lines 771-804):
```python
# Only triggered when "current_plan" is in node_update
if "current_plan" in node_update:
    current_plan = node_update.get("current_plan")
    if current_plan:
        # ... emit plan_update event ...
        
        # Emit step_progress for current step
        if hasattr(current_plan, 'steps') and current_plan.steps:
            # Calculate current step based on completed steps
            completed_count = sum(...)
            current_step_idx = min(completed_count, len(current_plan.steps) - 1)
            
            yield _make_event("step_progress", {
                "step_title": current_step.title,
                "step_index": current_step_idx,
                "total_steps": len(current_plan.steps),
                ...
            })
```

**Problem**: This code only runs when `current_plan` is in the node_update, which happens once.

### Frontend (`web/src`)

The frontend is correctly set up to handle step_progress events:
- ✅ `StepProgressEvent` interface defined in `core/api/types.ts`
- ✅ `mergeStepProgressMessage` function in `core/messages/merge-message.ts`
- ✅ `StepProgressIndicator` component in `research-activities-block.tsx`

The frontend code is working correctly - it's just not receiving the events.

## Why It's Not Working

1. **Plan is created once**: The planner creates a plan with steps (e.g., "Step 1: Gather data", "Step 2: Analyze", "Step 3: Report")
2. **Plan is not updated**: As the workflow executes through different agents (researcher, coder, reporter), the `current_plan` is not updated in the state
3. **No step tracking**: The workflow doesn't track which step is currently being executed
4. **No progress events**: Without plan updates, no new step_progress events are emitted

## What's Missing

To fix this properly, we need:

1. **Step Tracking in State**: Add a `current_step_index` to the workflow state
2. **Step Transition Detection**: Detect when the workflow moves from one step to another
3. **Progress Event Emission**: Emit step_progress events when:
   - A step starts
   - A step completes
   - The workflow moves to the next step

## Potential Solutions

### Option 1: Track Step Progress in Workflow State (Recommended)

Modify the workflow graph to:
1. Add `current_step_index` to the state
2. Update it as steps are executed
3. Emit step_progress events based on state changes

**Pros**: Clean, accurate, follows the workflow architecture  
**Cons**: Requires significant changes to the workflow graph

### Option 2: Infer Progress from Agent Activity

Emit step_progress events based on which agent is active:
- Step 1 when researcher is active
- Step 2 when coder is active  
- Step 3 when reporter is active

**Pros**: Simpler, no workflow changes needed  
**Cons**: Less accurate, hardcoded mapping

### Option 3: Use Observations to Track Progress

The workflow already emits "observations" for step execution results. We could:
1. Count observations to determine current step
2. Emit step_progress when observations change

**Pros**: Uses existing data  
**Cons**: Observations don't always map 1:1 to steps

## Current Workaround

The frontend shows:
- Agent activity (which agent is working)
- Agent messages (what the agent is doing)
- Loading animation (workflow is in progress)

Users can see the workflow is progressing, but don't see explicit step-by-step progress like "Step 2/3: Analyzing data".

## Recommendation

Implement **Option 1** (Track Step Progress in Workflow State) for a proper, long-term solution. This would require:

1. Modify `src/graph/state.py` to add `current_step_index`
2. Update workflow nodes to increment the step index
3. Modify `src/server/app.py` to emit step_progress based on step index changes
4. Test with the frontend to verify progress updates

**Estimated Effort**: 2-3 hours

## Impact

**Current Impact**: Low  
- Workflow still executes correctly
- Users can see agent activity
- Only the step-by-step progress indicator is missing

**User Experience**: Medium  
- Users would benefit from seeing explicit progress (e.g., "Step 2 of 3")
- Helps users understand how far along the workflow is
- Provides better transparency into the AI agent's process

---

**Documented By**: AI Assistant  
**Date**: November 27, 2025  
**Status**: Issue identified, solution proposed

