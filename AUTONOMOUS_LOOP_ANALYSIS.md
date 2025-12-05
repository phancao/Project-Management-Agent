# Autonomous Loop Analysis: Planning → Execute → Validate → Replan

## Current Flow (Missing Validation Loop)

```
coordinator
    ↓
planner (creates plan with steps)
    ↓
research_team (router)
    ↓
pm_agent/researcher/coder (executes step)
    ↓ (sets execution_res)
research_team (checks if all steps done)
    ↓
reporter (generates final report)
    ↓
END
```

### ❌ What's Missing: The Autonomous Loop

**Current behavior:**
1. **Plan once** → Planner creates a plan
2. **Execute blindly** → Each step executes without validation
3. **No feedback** → Agent doesn't check if step succeeded
4. **No replanning** → If step fails, workflow just continues or gets stuck
5. **Reporter at end** → Only generates report, doesn't validate results

**What should happen (Autonomous Agent Pattern):**
```
Planning Phase
    ↓
Execute Step
    ↓
Validate Results ← [MISSING]
    ├─ Success? → Next Step
    └─ Failure? → Replan/Retry ← [MISSING]
```

---

## Standard Autonomous Agent Pattern

### ReAct (Reason + Act)
```python
while not task_complete:
    # Reason
    thought = llm.think("What should I do next?")
    
    # Act
    action = llm.choose_action(available_actions)
    result = execute(action)
    
    # Observe & Validate
    observation = validate(result)
    
    # Reflect & Replan
    if observation.indicates_failure():
        replan()
    elif observation.indicates_success():
        next_step()
```

### Example: Cursor/Claude
```
Task: "Refactor function across 10 files"

Loop 1:
- Thought: "I need to search for the function first"
- Action: search_codebase("function_name")
- Observation: "Found in 10 files"
- Validation: ✅ Search successful
- Next: "Now I'll read each file"

Loop 2:
- Thought: "Reading file 1"
- Action: read_file("file1.ts")
- Observation: "File read, function at line 50"
- Validation: ✅ File exists, function found
- Next: "Edit this file"

Loop 3:
- Thought: "Refactoring file 1"
- Action: edit_file("file1.ts", changes)
- Observation: "Edit failed: syntax error"
- Validation: ❌ Syntax error detected
- Replan: "Need to fix syntax first, then retry"

Loop 4:
- Thought: "Fixing syntax error"
- Action: edit_file("file1.ts", corrected_changes)
- Observation: "Edit successful"
- Validation: ✅ Syntax correct
- Next: "Move to file 2"
```

**Key**: Each loop validates and can replan if needed.

---

## Current DeerFlow Implementation

### Where Validation SHOULD Happen

#### 1. After `pm_agent_node` Execution
**Current code (`src/graph/nodes.py`, line ~1790):**
```python
# Create a new Step with updated execution_res
updated_step = Step(
    need_search=current_step.need_search,
    title=current_step.title,
    description=current_step.description,
    step_type=current_step.step_type,
    execution_res=combined_result,  # ← Just stores result, no validation
)
```

**What's missing:**
- ❌ No check if `combined_result` indicates success/failure
- ❌ No LLM validation: "Did this step achieve its goal?"
- ❌ No decision: "Should I retry or continue?"

#### 2. In `research_team_node` (Router)
**Current code (`src/graph/builder.py`, line ~36):**
```python
def continue_to_running_research_team(state: State):
    # Check if all steps have execution_res (completed or failed)
    if all(step.execution_res for step in current_plan.steps):
        return "reporter"  # ← Goes to reporter even if steps failed
```

**What's missing:**
- ❌ No check if execution_res is an ERROR
- ❌ No LLM to validate: "Did this step succeed?"
- ❌ No route back to planner for replanning

#### 3. No Validation Node
**Missing from graph:**
- No `validator_node` to check step results
- No `reflection_node` to analyze what went wrong
- No path from `research_team` back to `planner` for replanning

---

## Proposed: Add Autonomous Loop

### New Architecture with Validation

```
coordinator
    ↓
planner (creates plan)
    ↓
research_team (router)
    ↓
pm_agent/researcher/coder (executes step)
    ↓
validator_node ← [NEW] (validates execution)
    ├─ Success? → research_team (next step)
    ├─ Partial? → research_team (continue with warning)
    └─ Failure? → reflection_node ← [NEW]
                      ↓
                  planner (replan with context)
```

### Implementation

#### Step 1: Add `validator_node`

```python
def validator_node(state: State, config: RunnableConfig) -> Command:
    """
    Validates the last executed step and decides next action.
    
    Possible outcomes:
    - success: Continue to next step
    - partial: Continue but flag issue
    - failure: Route to reflection for replanning
    """
    current_plan = state.get("current_plan")
    current_step_index = state.get("current_step_index", 0)
    
    # Get the step that was just executed
    if current_step_index >= len(current_plan.steps):
        return Command(goto="reporter")  # All done
    
    current_step = current_plan.steps[current_step_index]
    execution_res = current_step.execution_res
    
    # Use LLM to validate result
    validation_prompt = f"""
    Task: {current_step.title}
    Description: {current_step.description}
    Execution Result: {execution_res}
    
    Analyze if this step succeeded:
    1. Did it achieve the intended goal?
    2. Is the output valid and useful?
    3. Are there any errors or issues?
    
    Respond with JSON:
    {{
        "status": "success" | "partial" | "failure",
        "reason": "explanation",
        "should_retry": true | false,
        "suggested_fix": "what to do differently"
    }}
    """
    
    llm = get_llm_by_type("basic")
    validation_result = llm.invoke(validation_prompt)
    validation = json.loads(validation_result.content)
    
    # Route based on validation
    if validation["status"] == "success":
        logger.info(f"✅ Step '{current_step.title}' validated successfully")
        return Command(
            update={
                "validation_results": state.get("validation_results", []) + [validation]
            },
            goto="research_team"  # Continue to next step
        )
    
    elif validation["status"] == "partial":
        logger.warning(f"⚠️ Step '{current_step.title}' partially successful: {validation['reason']}")
        return Command(
            update={
                "validation_results": state.get("validation_results", []) + [validation]
            },
            goto="research_team"  # Continue with warning
        )
    
    else:  # failure
        logger.error(f"❌ Step '{current_step.title}' failed: {validation['reason']}")
        
        # Check if should retry or replan
        if validation["should_retry"] and state.get("retry_count", 0) < 3:
            # Retry same step
            return Command(
                update={
                    "retry_count": state.get("retry_count", 0) + 1,
                    "validation_results": state.get("validation_results", []) + [validation]
                },
                goto="research_team"  # Retry by routing back
            )
        else:
            # Need to replan
            return Command(
                update={
                    "validation_results": state.get("validation_results", []) + [validation],
                    "replan_reason": validation["reason"],
                    "replan_suggestion": validation["suggested_fix"]
                },
                goto="reflection"  # Route to reflection node
            )
```

#### Step 2: Add `reflection_node`

```python
def reflection_node(state: State, config: RunnableConfig) -> Command:
    """
    Reflects on failed execution and decides how to replan.
    
    This node analyzes what went wrong and provides context to planner
    for creating a better plan.
    """
    current_plan = state.get("current_plan")
    validation_results = state.get("validation_results", [])
    replan_reason = state.get("replan_reason", "Unknown failure")
    
    # Analyze all validation results to understand pattern
    reflection_prompt = f"""
    Original Plan: {current_plan.title}
    
    Steps executed:
    {json.dumps([{
        "title": step.title,
        "status": "completed" if step.execution_res else "pending",
        "result": step.execution_res[:200] if step.execution_res else None
    } for step in current_plan.steps], indent=2)}
    
    Validation Results:
    {json.dumps(validation_results, indent=2)}
    
    Failure Reason: {replan_reason}
    
    Reflect on what went wrong:
    1. Why did the current approach fail?
    2. What assumptions were incorrect?
    3. What alternative approach should we try?
    4. What additional information do we need?
    
    Provide a reflection that will help the planner create a better plan.
    """
    
    llm = get_llm_by_type("basic")
    reflection_result = llm.invoke(reflection_prompt)
    
    logger.info(f"🤔 Reflection: {reflection_result.content}")
    
    # Add reflection to state and route back to planner
    return Command(
        update={
            "reflection": reflection_result.content,
            "plan_iterations": state.get("plan_iterations", 0) + 1,
            "retry_count": 0,  # Reset retry count for new plan
        },
        goto="planner"  # Create new plan with reflection context
    )
```

#### Step 3: Update `planner_node`

```python
def planner_node(state: State, config: RunnableConfig) -> Command:
    """
    Enhanced planner that considers previous failures and reflections.
    """
    plan_iterations = state.get("plan_iterations", 0)
    reflection = state.get("reflection", None)
    
    # Build planning context
    planning_context = {
        "query": state.get("research_topic"),
        "iteration": plan_iterations
    }
    
    # If this is a replan, include reflection
    if reflection:
        planning_context["previous_attempt"] = {
            "plan": state.get("current_plan"),
            "reflection": reflection,
            "what_failed": state.get("replan_reason")
        }
        
        logger.info(f"🔄 Replanning (iteration {plan_iterations}) with reflection")
    
    # Create/update plan with reflection context
    plan_prompt = apply_prompt_template("planner", planning_context, configurable)
    
    # Add reflection context if available
    if reflection:
        plan_prompt.append(HumanMessage(
            content=f"""
            IMPORTANT: The previous plan failed. Here's the reflection:
            
            {reflection}
            
            Create a NEW plan that addresses these issues. Consider:
            1. Different approach or tools
            2. More specific steps
            3. Additional validation steps
            4. Fallback options
            """
        ))
    
    # ... rest of planner logic ...
```

#### Step 4: Update Graph

```python
def _build_base_graph():
    """Build graph with validation loop."""
    builder = StateGraph(State)
    
    # Existing nodes
    builder.add_node("coordinator", coordinator_node)
    builder.add_node("planner", planner_node)
    builder.add_node("research_team", research_team_node)
    builder.add_node("pm_agent", pm_agent_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("coder", coder_node)
    builder.add_node("reporter", reporter_node)
    
    # NEW NODES for autonomous loop
    builder.add_node("validator", validator_node)
    builder.add_node("reflection", reflection_node)
    
    # Edges
    builder.add_edge(START, "coordinator")
    builder.add_edge("coordinator", "planner")
    
    # Key change: After agent execution, go to validator
    builder.add_edge("pm_agent", "validator")
    builder.add_edge("researcher", "validator")
    builder.add_edge("coder", "validator")
    
    # Validator routes to:
    # - research_team (success/partial, continue)
    # - reflection (failure, need replan)
    builder.add_conditional_edges(
        "validator",
        lambda state: state.get("next_node", "research_team"),
        ["research_team", "reflection"]
    )
    
    # Reflection routes back to planner
    builder.add_edge("reflection", "planner")
    
    # Research team still routes to agents or reporter
    builder.add_conditional_edges(
        "research_team",
        continue_to_running_research_team,
        ["planner", "researcher", "coder", "pm_agent", "reporter"]
    )
    
    builder.add_edge("reporter", END)
    
    return builder
```

---

## Benefits of Autonomous Loop

### 1. Self-Correcting
```
❌ Before: Step fails → Workflow continues with error → Bad report
✅ After:  Step fails → Validates → Reflects → Replans → Tries again
```

### 2. Intelligent Retry
```
❌ Before: Blind retry 3x → Still fails → Give up
✅ After:  Validates result → If similar error, replans with different approach
```

### 3. Learning from Failure
```
❌ Before: Error logged, context lost
✅ After:  Reflection captures: "Why failed? What to try instead?"
```

### 4. Better Token Management
```
❌ Before: Accumulates all results → 27k tokens → Overflow
✅ After:  Validates early → Stops bad paths → Saves tokens
```

---

## Example: Autonomous Loop in Action

### Scenario: "Analyze Sprint 5"

#### Iteration 1: Initial Plan Fails
```
Planner: Creates plan
  1. List sprints
  2. Get sprint report for Sprint 5
  3. Generate burndown chart

PM Agent: Executes step 1
  Result: Returns 10 sprints, Sprint 5 is sprint_id=478

Validator: Validates step 1
  Status: ✅ Success
  Reason: "Found 10 sprints, Sprint 5 identified"

PM Agent: Executes step 2
  Result: ERROR - UUID expected, got '478'

Validator: Validates step 2
  Status: ❌ Failure
  Reason: "Database error - project_id '478' is not a UUID"
  Should retry: false
  Suggested fix: "Need to get full project context with UUID"

Reflection: Analyzes failure
  Problem: "The ID '478' is a numeric project key, not a UUID"
  Root cause: "Need to map project_key to provider UUID first"
  Better approach: "Add step to resolve project_key to UUID"
```

#### Iteration 2: Replanned with Reflection
```
Planner: Creates NEW plan (with reflection context)
  1. List sprints
  2. Resolve project_key to provider details ← [NEW STEP]
  3. Get sprint report using correct UUID
  4. Generate burndown chart

PM Agent: Executes step 2
  Result: project_key='478' → provider_id='uuid-abc-123'

Validator: Validates step 2
  Status: ✅ Success

PM Agent: Executes step 3 (with correct UUID)
  Result: Sprint report data

Validator: Validates step 3
  Status: ✅ Success

... continues successfully ...
```

**Result**: Self-corrected and succeeded instead of getting stuck!

---

## Implementation Checklist

- [ ] Create `validator_node` with LLM-based validation
- [ ] Create `reflection_node` for failure analysis
- [ ] Update `planner_node` to accept reflection context
- [ ] Update graph to include validation loop
- [ ] Add `validation_results` to State
- [ ] Add `reflection` to State
- [ ] Update routing logic in `research_team`
- [ ] Add max replanning limit (e.g., 3 iterations)
- [ ] Test with intentional failures
- [ ] Measure improvement in success rate

---

## Conclusion

**Current architecture is good** - multi-agent, flexible, powerful.

**What's missing**: The autonomous loop that makes agents truly intelligent:
- **Planning** → Create plan
- **Execute** → Run steps
- **Validate** → Check results ← [MISSING]
- **Reflect** → Analyze failures ← [MISSING]
- **Replan** → Try different approach ← [MISSING]

Adding this loop will make the system:
- ✅ Self-correcting
- ✅ More reliable
- ✅ Better at handling failures
- ✅ Truly autonomous

This is the difference between:
- **Current**: "Programmed workflow" (fixed path)
- **With loop**: "Autonomous agent" (adapts and learns)


