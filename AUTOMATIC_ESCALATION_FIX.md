# Automatic Escalation to Full Pipeline ✅

## Problem Fixed

**User Issue:** "Even if it fallback to full analytic, it still failed why?"

**Root Cause:** **It NEVER fallbacked!** When ReAct succeeded but data was too large, the system had NO automatic escalation mechanism.

---

## The Fix: Smart Data Size Detection

### Before (Broken Flow)

```
User: "analyse sprint 5"
    ↓
[COORDINATOR] → ReAct (fast path)
    ↓
[REACT-AGENT] ✅ Calls PM tools
               ✅ Gets ALL data at once (21,492 tokens)
               ✅ "Success!" → Routes to REPORTER
    ↓
[REPORTER] ❌ Context overflow!
           ❌ "Data too large (21,492 vs 16,385 limit)"
           ❌ Shows error to user
    ↓
[END] ← Game over, no retry! ❌
```

**Result:** User sees error, no solution

---

### After (Fixed Flow)

```
User: "analyse sprint 5"
    ↓
[COORDINATOR] → ReAct (fast path)
    ↓
[REACT-AGENT] ✅ Calls PM tools
               ✅ Gets data (21,492 tokens)
               ⚠️  Detects: "Data too large for reporter!"
               ⬆️  ESCALATE to full pipeline
    ↓
[PLANNER] 📋 Creates multi-step plan:
          Step 1: Get sprint info
          Step 2: Get sprint report
          Step 3: Get burndown data
    ↓
[PM_AGENT] Executes Step 1 → Gets data
    ↓
[VALIDATOR] ✅ Validates + Compresses
    ↓
[PM_AGENT] Executes Step 2 → Gets data
    ↓
[VALIDATOR] ✅ Validates + Compresses
    ↓
... (incremental processing)
    ↓
[REPORTER] ✅ Generates report with compressed data
    ↓
[END] ✅ Success! Full analysis delivered
```

**Result:** User gets complete analysis (takes longer but works!)

---

## What Changed

### New Trigger in ReAct: Data Size Check

**File:** `src/graph/nodes.py` (react_agent_node, line ~3105)

```python
# Trigger 4: Data too large for reporter (NEW!)
from src.utils.context_manager import ContextManager

# Count tokens in the ReAct output
output_tokens = ContextManager._count_tokens_with_tiktoken([
    {"role": "assistant", "content": output}
])

# Count tokens in current state (rough estimate)
state_messages = state.get("messages", [])
state_tokens = sum(
    len(str(msg.content)) // 4  # 1 token ≈ 4 chars
    for msg in state_messages[-5:]  # Last 5 messages
)

total_estimated_tokens = output_tokens + state_tokens

# Get reporter's token limit (85% of model's context)
model_limit = get_llm_token_limit_by_type("basic") or 16385
reporter_limit = int(model_limit * 0.85)  # Reporter uses 85%

# If data is too large, escalate!
if total_estimated_tokens > reporter_limit:
    logger.warning(
        f"[REACT-AGENT] ⬆️ Data too large ({total_estimated_tokens} tokens > {reporter_limit} limit) - "
        "escalating to full pipeline for incremental processing"
    )
    return Command(
        update={
            "escalation_reason": f"data_too_large ({total_estimated_tokens} tokens vs {reporter_limit} limit)",
            "react_attempts": intermediate_steps,
            "partial_result": output,
            "goto": "planner"
        },
        goto="planner"
    )
```

---

## ReAct Escalation Triggers (Complete List)

ReAct now escalates to full pipeline in **4 scenarios**:

| Trigger | Condition | Reason |
|---------|-----------|--------|
| **1. Too many iterations** | `>= 8 iterations` | Agent is struggling |
| **2. Repeated errors** | `>= 3 errors` | Tools are failing |
| **3. Agent requests planning** | Output contains "requires detailed planning" | Complex task detected |
| **4. Data too large (NEW!)** | `tokens > 85% of reporter limit` | Prevent reporter overflow |

---

## Why Full Pipeline Handles Large Data Better

### ReAct (Fast Path)
- ⚡ One-shot execution
- ✅ Great for simple queries
- ❌ Gets ALL data at once
- ❌ No compression between steps
- ❌ If data is huge → fails

### Full Pipeline (Comprehensive)
- 🏗️ Multi-step execution
- ✅ Incremental data loading
- ✅ Validator compresses after EACH step
- ✅ Handles large datasets gracefully
- ✅ Retry logic per step

**Example: "analyse sprint 5"**

**ReAct approach:**
```
Call sprint_report() → Get 21K tokens at once → Send to reporter → FAIL ❌
```

**Full Pipeline approach:**
```
Step 1: list_sprints()        → Get 500 tokens  → Validate → Compress
Step 2: sprint_report()       → Get 8K tokens   → Validate → Compress
Step 3: burndown_chart()      → Get 4K tokens   → Validate → Compress
Step 4: list_tasks_in_sprint()→ Get 6K tokens   → Validate → Compress
                                                  ↓
Reporter: Receives 12K tokens (compressed from 18.5K) → SUCCESS ✅
```

---

## Expected Behavior Now

### Try: "analyse sprint 5"

**Scenario 1: Small dataset (< 13K tokens)**
```
Flow: ReAct → Reporter → Success
Time: ~5-7 seconds
Result: ✅ Quick answer
```

**Scenario 2: Large dataset (> 13K tokens)**
```
Flow: ReAct → Detects size → Escalates → Planner → PM_Agent → Validator → Reporter → Success
Time: ~20-30 seconds
Result: ✅ Full comprehensive report
Logs: "[REACT-AGENT] ⬆️ Data too large (21492 tokens > 13927 limit) - escalating to full pipeline"
```

**Scenario 3: Very complex query**
```
Flow: ReAct → Agent requests planning → Escalates → Full Pipeline
Time: ~30-40 seconds
Result: ✅ Multi-step analysis
```

---

## Test It! 🚀

**Try these queries:**

1. **Simple query (should use ReAct):**
   ```
   "How many tasks in sprint 5?"
   ```
   Expected: Fast path (5s), direct answer

2. **Large data query (should escalate):**
   ```
   "analyse sprint 5"
   ```
   Expected: Auto-escalate (25s), full report

3. **Complex query (should escalate):**
   ```
   "Compare sprint 4 and sprint 5 velocity and predict sprint 6"
   ```
   Expected: Auto-escalate (30s), comprehensive analysis

---

## Logs to Watch For

### Successful Escalation
```
[REACT-AGENT] 🚀 Starting fast ReAct agent
[REACT-AGENT] ✅ Loaded 15 PM tools + web_search
[REACT-AGENT] Token check: output=12450, state=2100, total=14550, reporter_limit=13927
[REACT-AGENT] ⬆️ Data too large (14550 tokens > 13927 limit) - escalating to full pipeline
[COORDINATOR] 📊 Using full pipeline: escalation=data_too_large (14550 tokens vs 13927 limit)
[PLANNER] 📋 Creating multi-step plan...
[PM_AGENT] Executing Step 1...
[VALIDATOR] ✅ Validation passed, data within limits
...
[REPORTER] ✅ Generated final report
```

### No Escalation Needed
```
[REACT-AGENT] 🚀 Starting fast ReAct agent
[REACT-AGENT] Token check: output=2450, state=800, total=3250, reporter_limit=13927
[REACT-AGENT] ✅ Success - returning answer (156 chars)
[REPORTER] ✅ Generated final report
```

---

## Summary

✅ **Fixed:** ReAct now detects data size BEFORE routing to reporter
✅ **Added:** Automatic escalation when data > 85% of reporter limit
✅ **Result:** Full pipeline handles large datasets via incremental processing
✅ **UX:** Users get results instead of errors (just takes longer)

**Key insight:** Fast path (ReAct) is optimistic but smart enough to escalate when needed. Full pipeline is the fallback for complex/large data scenarios.


