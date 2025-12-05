# Background Investigation - New Architecture

## ✅ NEW APPROACH (Implemented)

**Background Investigation is now a TOOL for ReAct, not a separate routing step.**

### The Flow

```
OLD (Removed):
User: "Analyze sprint 5"
    ↓
Background Investigator: Web search BEFORE planning
    ↓
Planner: Creates plan
    ↓
Execute steps

NEW (Current):
User: "Analyze sprint 5"
    ↓
ReAct Agent: Has PM tools + web_search tool
    ↓
    - Tries PM tools first (fast)
    - Uses web_search IF needed for context
    - Self-corrects and adapts
    ↓
Final Answer (or escalate to full pipeline if struggling)
```

## Key Benefits

1. **Faster**: No pre-planning web search delay
2. **Smarter**: ReAct decides WHEN to search (not always)
3. **Adaptive**: Can escalate to full pipeline if user unhappy

---

## Implementation

### Node: `background_investigation_node`

```python
def background_investigation_node(state: State, config: RunnableConfig):
    """
    Performs web search to gather context BEFORE planning.
    
    Purpose:
    - Research topics needing external knowledge
    - Get industry best practices
    - Gather reference information
    
    NOT needed for:
    - Simple PM queries (data already in system)
    - Direct data retrieval (list tasks, show sprint)
    """
    query = state.get("research_topic")
    
    # Search the web
    search_tool = get_web_search_tool()
    results = search_tool.invoke(query)
    
    # Results are passed to planner
    return {
        "background_investigation_results": results
    }
```

### When It's Used

Configured in `src/graph/types.py`:
```python
class State(MessagesState):
    enable_background_investigation: bool = True  # Default: ON
```

**Triggered when:**
- User query needs external research
- Default behavior in DeerFlow

**Examples:**

**Should Use Background Investigation:**
```
❌ "Analyze sprint 5" → No need (PM data in system)
✅ "Research agile best practices and create plan" → Yes (needs web research)
✅ "What are industry trends in project management?" → Yes (external knowledge)
✅ "Compare our velocity to industry standards" → Yes (needs benchmarks)
```

---

## The Problem

### Why It Conflicts with Adaptive Routing

**Current behavior:**
```python
# Step 1: Adaptive routing says "use ReAct"
if goto == "planner":
    goto = "react_agent"  # ✅ Set to react_agent

# Step 2: Background investigation overrides it
if goto == "planner" and enable_background_investigation:
    goto = "background_investigator"  # ❌ Overrides! (but goto is "react_agent", not "planner")
```

Wait, that shouldn't happen because the check is `if goto == "planner"` and we already changed it to `"react_agent"`...

Let me check the actual code order in the file.

---

## The Fix

**Priority order should be:**

```python
# 1. Check user escalation first
if previous_result and user_wants_more:
    goto = "planner"  # User needs detailed analysis

# 2. Check if first-time query → Use ReAct (FAST)
elif goto == "planner" and not escalation_reason:
    goto = "react_agent"  # Optimistic fast path

# 3. Only if still routing to planner, check background investigation
elif goto == "planner" and enable_background_investigation:
    goto = "background_investigator"  # For research queries
```

**Reasoning:**
- ReAct can handle most PM queries WITHOUT web search
- Background investigation only needed for research tasks
- Simple PM query: react_agent → PM tools → answer (fast)
- Research query: background_investigator → planner → research (slow but thorough)

---

## When to Use Background Investigation

### Use It (enable_background_investigation = True):
- ✅ Research queries needing external knowledge
- ✅ "Best practices" questions
- ✅ Industry benchmarking
- ✅ Strategic planning with context

### Skip It (go straight to ReAct):
- ✅ Simple PM queries ("list tasks")
- ✅ Data retrieval ("show sprint 5")
- ✅ Analysis of existing data ("sprint performance")
- ✅ 80% of typical PM queries

---

## Implementation Details

### ReAct Agent Tools

```python
# ReAct agent now has BOTH PM tools AND web_search
pm_tools = await get_pm_tools(config)  # PM-specific tools
search_tool = get_web_search_tool()     # Web search for context
tools = pm_tools + [search_tool]
```

### ReAct Prompt

```
You are a PM assistant with access to:
- PM tools (list_sprints, sprint_report, etc.)
- web_search (for external context)

Strategy:
1. Start with PM tools for data retrieval
2. Use web_search ONLY if you need external context:
   - Best practices
   - Industry benchmarks
   - Standards and methodologies
3. Self-correct if errors occur
4. Escalate to full pipeline if too complex
```

### Escalation Flow

```
User: "Analyze sprint 5"
    ↓
ReAct: Tries PM tools → Success → Answer (3-5s)
    ↓
User: "I need more detailed analysis with benchmarks"
    ↓
Coordinator: Detects escalation → Routes to Planner
    ↓
Full Pipeline: background_investigator → planner → execute → validate → report (30s)
```

---

## Current Status

**✅ IMPLEMENTED:**
- ✅ ReAct is the default fast path for all queries
- ✅ ReAct has PM tools + web_search (decides when to use it)
- ✅ Background investigation removed as separate routing step
- ✅ User escalation triggers full pipeline with comprehensive analysis
- ✅ Adaptive routing based on query complexity

**Test Scenarios:**

| Query | Expected Flow | Time | Web Search? |
|-------|--------------|------|-------------|
| "Analyze sprint 5" | ReAct → PM tools → Answer | 3-5s | No (unless ReAct decides) |
| "Show me sprint 5 with industry benchmarks" | ReAct → PM tools + web_search → Answer | 5-8s | Yes (ReAct uses web_search) |
| "I need comprehensive analysis" | Coordinator → Planner (full pipeline) | 25-35s | Yes (via research steps) |
| Follow-up: "need more detail" | Coordinator → Planner (escalation) | 25-35s | Yes (comprehensive) |

**Key Insight:**
Web search is now **on-demand** (ReAct decides) rather than **pre-emptive** (always before planning).

