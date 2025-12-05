# Duplicate Steps Fix V2 - Routing Conflict Resolution

## The Problem (Still Happening)

Steps were still being executed **3 times** even after the first fix. The root cause was a **routing conflict** between:
1. `research_team_node` returning `Command(goto="reporter")`
2. `continue_to_running_research_team` conditional edge routing to `validator`

## Root Cause Analysis

### The Flow That Caused Duplicates:

```
1. research_team → continue_to_running_research_team → validator (when all steps complete)
2. validator validates → success → routes to research_team
3. research_team → continue_to_running_research_team → validator (again!)
4. Loop continues... (3 times = 9 steps total)
```

### Why It Happened:

1. **`research_team_node`** (line 1837) was returning `Command(goto="reporter")` when all steps complete
2. **`continue_to_running_research_team`** (line 39-43) was routing to `validator` when all steps complete
3. **LangGraph behavior**: Conditional edge functions **override** `Command.goto` return values
4. So `research_team_node`'s `Command(goto="reporter")` was being ignored
5. The conditional edge routed to `validator` instead
6. `validator` validated successfully and routed back to `research_team`
7. This created an infinite loop until max iterations

## The Fix

### Fix 1: Remove Command Return from research_team_node

**Changed:**
- Removed `return Command(goto="reporter")` from `research_team_node`
- Added comment explaining that routing is handled by conditional edge function
- This prevents conflicts between Command.goto and conditional edge routing

**Code:**
```python
def research_team_node(state: State):
    # Check if all steps are complete (for logging only)
    current_plan = state.get("current_plan")
    if current_plan and not isinstance(current_plan, str) and current_plan.steps:
        all_complete = all(step.execution_res for step in current_plan.steps)
        if all_complete:
            logger.info(f"[research_team_node] All {len(current_plan.steps)} steps completed! Conditional edge will route to validator.")
    # No Command return - routing handled by conditional edge
```

### Fix 2: Validator Routes to Reporter When All Steps Complete

**Changed:**
- Added check in `validator_node` to see if all steps are complete
- If all steps complete AND validation succeeds, route directly to `reporter`
- This prevents the loop back to `research_team`

**Code:**
```python
if validation["status"] == "success":
    logger.info(f"[VALIDATOR] ✅ Step validated successfully, continuing")
    
    # Check if all steps are now complete
    all_steps_complete = all(step.execution_res for step in current_plan.steps)
    if all_steps_complete:
        logger.info(f"[VALIDATOR] All {len(current_plan.steps)} steps completed and validated! Routing to reporter.")
        return Command(
            update={
                "validation_results": validation_results,
                "retry_count": 0
            },
            goto="reporter"
        )
    
    # Not all steps complete, continue to next step
    return Command(
        update={
            "validation_results": validation_results,
            "retry_count": 0
        },
        goto="research_team"
    )
```

## Expected Behavior After Fix

**New Flow:**
```
1. research_team → continue_to_running_research_team → validator (when all steps complete)
2. validator validates → success → checks if all steps complete → YES
3. validator routes to reporter → END
```

**Result:**
- Steps execute once (or retry if validation fails)
- No infinite loops
- No duplicate steps
- Clean routing to reporter when done

## Testing

Test with: `analyse sprint 10`

**Expected:**
- Steps execute once (3 tool calls: List Sprints, Sprint Report, Burndown Chart)
- Validator validates each step
- When all steps complete, validator routes directly to reporter
- No duplicate executions
- No routing loops


