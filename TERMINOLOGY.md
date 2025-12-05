# DeerFlow Terminology Guide 📚

## Workflow Modes

### 1. **Fast Path (ReAct Agent)** ⚡

**What it is:**
- Single-agent approach using **ReAct pattern** (Reasoning + Acting)
- Handles 80% of queries quickly
- Direct tool calling without multi-step planning

**Flow:**
```
User Query → Coordinator → ReAct Agent → Tools → Reporter → User
```

**Example:**
```
User: "analyse sprint 5"
[REACT-AGENT] Thought: I need Sprint 5's ID
[REACT-AGENT] Action: list_all_sprints()
[REACT-AGENT] Observation: Found Sprint 5 (id: abc-123)
[REACT-AGENT] Action: sprint_report(abc-123)
[REACT-AGENT] Final Answer: Sprint 5 had 23 tasks, 18 completed...
→ Response time: ~5-10 seconds
```

**When used:**
- Simple queries (sprint analysis, task listing, project status)
- Clear intent (no ambiguity)
- No need for comprehensive planning

**Auto-escalates if:**
- Too many iterations (>8) → Agent is struggling
- Multiple errors (>2) → Tools failing
- Agent explicitly requests: "This requires detailed planning"

---

### 2. **Full Pipeline (Comprehensive Workflow)** 📊

**What it is:**
- Multi-agent orchestrated approach
- Creates explicit plan with steps
- Executes, validates, reflects, and replans if needed
- Handles complex queries requiring coordination

**Flow:**
```
User Query → Coordinator → Planner → Research Team → 
(Execute Steps) → Validator → (If issues) → Reflector → 
(Replan) → Reporter → User
```

**Full Pipeline Components:**

#### **Coordinator**
- Routes queries to appropriate agent
- Handles clarification if needed
- Detects user escalation requests

#### **Planner**
- Creates structured multi-step plan
- Example plan for "comprehensive sprint 5 analysis":
  ```
  Step 1: List all sprints → Get Sprint 5 ID
  Step 2: Get sprint report → Metrics and summary
  Step 3: Get burndown chart → Track progress over time
  Step 4: List tasks in sprint → Detailed task breakdown
  Step 5: Analyze blockers → Identify issues
  ```

#### **Research Team**
- Coordinates execution of plan steps
- Routes to appropriate specialized agents:
  - **Researcher**: Web searches, external research
  - **PM Agent**: PM tool calls (sprint reports, task lists, etc.)
  - **Coder**: Code-related tasks

#### **Validator**
- Checks if plan execution succeeded
- Validates output quality
- Triggers replanning if issues found

#### **Reflector**
- Analyzes failures
- Provides feedback for replanning
- Example: "Step 2 failed because sprint_id was invalid. 
           Reflection: Need to extract sprint_id from Step 1 results first."

#### **Reporter**
- Aggregates results from all steps
- Generates final comprehensive report
- Formats output for user

**Example Full Pipeline:**
```
User: "comprehensive analysis of sprint 5 with detailed breakdown"

[PLANNER] Creating plan...
Plan created:
  1. List sprints → Get Sprint 5 details
  2. Get sprint report → Core metrics
  3. Get burndown chart → Progress tracking
  4. List tasks → Task breakdown
  5. Analyze team performance

[RESEARCH-TEAM] Executing Step 1...
[PM-AGENT] Calling list_all_sprints()
[RESEARCH-TEAM] Step 1 complete ✓

[RESEARCH-TEAM] Executing Step 2...
[PM-AGENT] Calling sprint_report(sprint_id=abc-123)
[RESEARCH-TEAM] Step 2 complete ✓

... (continues for all 5 steps)

[VALIDATOR] Checking plan execution...
[VALIDATOR] All steps completed successfully ✓

[REPORTER] Generating comprehensive report...
→ Response time: ~30-40 seconds

Final Report:
# Sprint 5 Comprehensive Analysis
## Overview
Sprint 5 (Oct 1 - Oct 14) completed with 78% success rate...
## Metrics
- Tasks completed: 18/23
- Story points: 45/60
...
(detailed multi-section report)
```

**When used:**
- User explicitly asks: "comprehensive", "detailed", "full analysis", "in-depth"
- ReAct agent escalates due to complexity
- User says "need more detail" after ReAct's quick answer
- Complex multi-step queries

---

## Adaptive Routing Strategy

**How DeerFlow chooses:**

```
┌─────────────────────────────────────────────────┐
│ User Query: "analyse sprint 5"                  │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ Coordinator checks:                             │
│ • Is it a follow-up? (previous_result exists)   │
│ • User wants "comprehensive"?                   │
│ • Escalation from ReAct?                        │
└─────────────────────────────────────────────────┘
                      ↓
         ┌────────────┴────────────┐
         NO                        YES
         ↓                          ↓
┌─────────────────┐      ┌──────────────────────┐
│ ⚡ ReAct         │      │ 📊 Full Pipeline      │
│ (Fast Path)     │      │ (Comprehensive)      │
│ ~5-10s          │      │ ~30-40s              │
└─────────────────┘      └──────────────────────┘
         │
         ↓
  ┌─────────────┐
  │ Success?    │
  └─────────────┘
    YES ↓   NO ↓
        ↓       ↓
   Reporter  Escalate to Full Pipeline
```

---

## Comparison: Fast Path vs Full Pipeline

| Feature | Fast Path (ReAct) | Full Pipeline |
|---------|------------------|---------------|
| **Speed** | ⚡ 5-10 seconds | 📊 30-40 seconds |
| **Use Case** | Simple queries | Complex analysis |
| **Agents** | 1 (ReAct) | 5+ (Coordinator, Planner, Research Team, Validator, Reflector, Reporter) |
| **Planning** | ❌ No explicit plan | ✅ Multi-step plan |
| **Validation** | ❌ No validation | ✅ Validates & replans |
| **Self-correction** | ⚠️ Limited (3 errors max) | ✅ Full autonomous loop |
| **Output** | Quick answer | Comprehensive report |
| **Example Query** | "show sprint 5" | "comprehensive sprint 5 analysis with team performance breakdown" |

---

## Auto-Escalation Triggers

**ReAct → Full Pipeline escalation happens when:**

1. **Too many iterations** (>8)
   - ReAct is looping, unable to complete task
   - Example: Keeps calling wrong tools

2. **Multiple errors** (>2)
   - Tool calls failing repeatedly
   - Example: 404 errors, invalid parameters

3. **Agent self-awareness**
   - ReAct explicitly says: "This requires detailed planning"
   - Example: Query too complex for single-agent approach

4. **User feedback**
   - User replies: "need more detail", "not enough", "comprehensive analysis"
   - Coordinator detects dissatisfaction → escalates

---

## Real-World Examples

### Example 1: Fast Path Success ✅

```
User: "what's sprint 3 status?"

[COORDINATOR] ⚡ Using ReAct fast path
[REACT-AGENT] Starting...
[REACT-AGENT] list_all_sprints() → Found Sprint 3
[REACT-AGENT] sprint_report() → Got status
[REACT-AGENT] Final Answer: Sprint 3 is ACTIVE, 12/15 tasks done
→ 7 seconds
```

### Example 2: Fast Path → Escalation → Full Pipeline ⚠️

```
User: "analyse sprint 5"

[COORDINATOR] ⚡ Using ReAct fast path
[REACT-AGENT] Starting...
[REACT-AGENT] sprint_report(sprint_id="5") → 404 Error
[REACT-AGENT] sprint_report(sprint_id="Sprint 5") → 404 Error
[REACT-AGENT] list_sprints() → Got IDs
[REACT-AGENT] sprint_report(sprint_id=malformed) → 404 Error
[REACT-AGENT] ⬆️ Multiple errors (3) - escalating

[COORDINATOR] 📊 Routing to Full Pipeline
[PLANNER] ⚡ ESCALATION FROM REACT AGENT
[PLANNER] Creating better plan...
[PLANNER] Plan:
  1. List sprints properly
  2. Extract correct sprint_id
  3. Get sprint report
  
[RESEARCH-TEAM] Executing...
[VALIDATOR] Checking...
[REPORTER] Generating report...
→ 35 seconds
```

### Example 3: User-Requested Full Pipeline 📊

```
User: "comprehensive analysis of sprint 5 with team performance, 
       velocity trends, and detailed task breakdown"

[COORDINATOR] 📊 User wants "comprehensive" - Using Full Pipeline
[PLANNER] Creating detailed plan...
(Full pipeline executes with 7 steps)
→ 42 seconds

Result: Multi-section comprehensive report
```

---

## Summary

**"Full Pipeline"** = Comprehensive multi-agent workflow with planning, execution, validation, and reflection

**"Fast Path"** = Quick single-agent ReAct approach for simple queries

**Adaptive Routing** = Automatically choose the right approach based on query complexity and agent performance

The system **optimistically uses Fast Path first**, then **intelligently escalates to Full Pipeline** only when needed!


