# Agent Flow Diagram - When PM_Agent is Called

## Main Flow

```
START
  ↓
coordinator
  ↓ (adaptive routing)
  ├─→ react_agent (FAST PATH - first-time queries, optimistic)
  │     ↓ (executes with PM tools + web_search)
  │     ├─→ reporter (if successful)
  │     └─→ planner (if escalates - too complex, errors, or explicit request)
  │
  ├─→ planner (FULL PIPELINE - complex queries, escalations, PM queries)
  │     ↓ (creates plan with steps)
  │     └─→ research_team → pm_agent/researcher/coder loop
  │
  └─→ background_investigator → planner
```

## ReAct Agent Flow (Fast Path)

```
coordinator
  ↓ (adaptive routing: first query → react_agent)
react_agent
  ↓ (has access to PM tools + web_search)
  ├─→ reporter (if successful - simple query handled)
  └─→ planner (if escalates - complex query needs full pipeline)
```

**ReAct Agent Escalation Triggers:**
- Too many iterations (>8)
- Repeated errors (>2)
- Agent explicitly requests planning
- Scratchpad exceeds token limit

## PM Agent Execution Loop

```
planner
  ↓ (creates plan with steps)
research_team
  ↓ (continue_to_running_research_team function checks step_type)
  ├─→ pm_agent (if step_type == PM_QUERY)
  ├─→ researcher (if step_type == RESEARCH)
  ├─→ coder (if step_type == PROCESSING)
  ├─→ validator (if all steps complete)
  └─→ planner (if no steps or error)
```

## PM Agent Loop Details

```
pm_agent
  ↓ (executes step, calls PM tools)
validator
  ↓ (validates step execution result)
  ├─→ research_team (if step succeeded → continue to next step)
  ├─→ reflector (if step failed → replan)
  ├─→ reporter (if all steps done)
  └─→ __end__ (if reporter already completed)
```

## Complete Flow Examples

### Example 1: Simple PM Query (ReAct Fast Path)

```
1. START → coordinator
2. coordinator → react_agent (first query, optimistic routing)
3. react_agent → (executes with PM tools directly)
4. react_agent → reporter (simple query handled successfully)
5. reporter → END
```

### Example 2: Complex PM Query (Full Pipeline)

```
1. START → coordinator
2. coordinator → react_agent (first query, optimistic routing)
3. react_agent → planner (escalates - too complex or errors)
4. planner → research_team (plan created with 3 steps)
5. research_team → pm_agent (Step 1: step_type=PM_QUERY)
6. pm_agent → validator (Step 1 executed)
7. validator → research_team (Step 1 succeeded)
8. research_team → pm_agent (Step 2: step_type=PM_QUERY)
9. pm_agent → validator (Step 2 executed)
10. validator → research_team (Step 2 succeeded)
11. research_team → coder (Step 3: step_type=PROCESSING)
12. coder → validator (Step 3 executed)
13. validator → research_team (Step 3 succeeded)
14. research_team → validator (all steps complete)
15. validator → reporter (all steps validated)
16. reporter → END
```

### Example 3: Direct Full Pipeline (No ReAct)

```
1. START → coordinator
2. coordinator → planner (escalation_reason exists or previous_result exists)
3. planner → research_team (plan created)
4. research_team → pm_agent (loop continues...)
5. ... (same as Example 2 steps 5-16)
```

## Key Routing Functions

### `continue_to_running_research_team()` (in builder.py)
- **Purpose**: Routes to the appropriate agent based on step_type
- **Logic**:
  - Finds first incomplete step (no execution_res)
  - Checks step.step_type:
    - `StepType.PM_QUERY` → `pm_agent`
    - `StepType.RESEARCH` → `researcher`
    - `StepType.PROCESSING` → `coder`
  - If all steps complete → `validator`
  - If stuck (retried 3+ times) → `reporter`

### `route_from_validator()` (in builder.py)
- **Purpose**: Routes after step validation
- **Logic**:
  - Default: `research_team` (continue to next step)
  - If step failed: `reflector` (replan)
  - If all done: `reporter` (generate final report)
  - If reporter already done: `__end__` (prevent infinite loop)

## When PM_Agent is Called

PM_Agent is called when:
1. **Full Pipeline Path**: After `planner` creates a plan with steps
2. **Step Type**: A step has `step_type == StepType.PM_QUERY`
3. **Routing**: `research_team` node routes to `pm_agent` via `continue_to_running_research_team()`
4. **Loop**: After execution, always goes to `validator`, which then routes back to `research_team` for the next step

**Note**: ReAct agent has direct access to PM tools and can handle simple PM queries without going through the full pipeline. It only escalates to planner (which then uses pm_agent) if the query is too complex.

## Loop Prevention

1. **Stuck Detection**: If same step retried 3+ times → route to reporter
2. **Final Report Check**: If `final_report` exists → route to `__end__`
3. **All Steps Complete**: If all steps have `execution_res` → route to validator → reporter
4. **ReAct Escalation**: ReAct agent auto-escalates to planner if query is too complex (prevents infinite loops)

## Key Differences: ReAct vs Full Pipeline

| Aspect | ReAct Agent | Full Pipeline (PM_Agent) |
|--------|-------------|-------------------------|
| **Entry** | coordinator → react_agent | coordinator → planner → research_team → pm_agent |
| **Planning** | No plan, direct execution | Creates plan with steps first |
| **Tools** | PM tools + web_search | PM tools only (via MCP) |
| **Use Case** | Simple queries | Complex multi-step queries |
| **Execution** | Single ReAct loop | Multi-step loop with validation |
| **Output** | Direct to reporter | Validated steps → reporter |
| **Escalation** | Auto-escalates to planner if needed | N/A (already in full pipeline) |

## The Role of ReAct Agent

### What is ReAct Pattern?

**ReAct = Reasoning + Acting**

The ReAct agent uses a **single autonomous loop** pattern:
1. **Reason**: Think about what to do next
2. **Act**: Call a tool (PM tool, web_search, etc.)
3. **Observe**: See the tool result
4. **Repeat**: Continue reasoning and acting until the query is answered

This happens in a **scratchpad** (internal memory) where the agent keeps track of:
- Its thoughts/reasoning
- Tool calls made
- Tool results received
- Next steps to take

### Why ReAct Agent Exists

**1. Speed & Efficiency**
- **No planning overhead**: Doesn't create a plan first
- **Direct execution**: Starts working immediately
- **Single agent loop**: No multi-agent coordination overhead

**2. Simplicity for Simple Queries**
- **80% of queries are simple**: "List users in project X", "Get sprint 4 tasks"
- **Don't need structured planning**: Can reason and act directly
- **Faster response**: Goes directly to reporter when done

**3. Adaptive Escalation**
- **Auto-detects complexity**: If query is too complex, escalates to full pipeline
- **Learns from attempts**: Passes its observations to planner when escalating
- **Best of both worlds**: Fast for simple, comprehensive for complex

### ReAct Agent Execution Flow

```
react_agent (single agent with scratchpad)
  ↓
  Loop:
    1. Reason: "I need to list users in project X"
    2. Act: Call list_users(project_id)
    3. Observe: Get user list
    4. Reason: "I have the data, I can now answer the query"
    5. Act: Generate final answer
  ↓
  Success → reporter
  OR
  Too complex/errors → planner (escalate)
```

### When ReAct Escalates to Full Pipeline

1. **Too many iterations** (>8): Query requires too many tool calls
2. **Repeated errors** (>2): Tools keep failing
3. **Explicit request**: Agent decides it needs structured planning
4. **Scratchpad overflow**: Token limit exceeded (accumulated too much context)

### Comparison: ReAct vs Full Pipeline

**ReAct Agent (Fast Path):**
- ✅ Fast: No planning, direct execution
- ✅ Simple: Single agent, single loop
- ✅ Efficient: Minimal overhead
- ❌ Limited: Can't handle very complex multi-step queries
- ❌ No validation: No step-by-step validation

**Full Pipeline (PM_Agent):**
- ✅ Comprehensive: Structured planning with steps
- ✅ Validated: Each step validated before next
- ✅ Complex: Handles multi-step, multi-agent workflows
- ❌ Slower: Planning overhead, multi-agent coordination
- ❌ More tokens: Plan creation, step validation, etc.

### Example: "List users in project X"

**ReAct Path:**
```
coordinator → react_agent
  ↓
react_agent: "I'll call list_users(project_id)"
  ↓
Tool: list_users returns 11 users
  ↓
react_agent: "I have the data, here's the answer"
  ↓
reporter → END
```
**Time**: ~2-3 seconds

**Full Pipeline Path:**
```
coordinator → planner
  ↓
planner: Creates plan with steps
  ↓
research_team → pm_agent
  ↓
pm_agent: Executes step 1
  ↓
validator: Validates step 1
  ↓
research_team → (check if more steps)
  ↓
reporter → END
```
**Time**: ~5-10 seconds

**Result**: ReAct is 2-3x faster for simple queries!

