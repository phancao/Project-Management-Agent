# Why 329K Tokens Even After Browser Reset?

## The Mystery

**User reports:** Even after resetting the browser, the system is trying to send **329K tokens**.

**Logs show:**
- `Original messages: 1` ✅ (Only 1 message in state)
- `Compressed tokens: 42` ✅ (Tiny)
- `Estimated total: 5,446` ✅ (Well under limit)
- **BUT:** Actual request: **328,913 tokens** ❌ (WAY over limit!)

## Root Cause Analysis

### The 329K Tokens Are NOT From `state["messages"]`

The logs clearly show:
- State only has **1 message** (the current query)
- Compressed to **42 tokens**
- Pre-flight check passes ✅

### Where Are The 329K Tokens Coming From?

The 329K tokens are coming from **LangChain's ReAct AgentExecutor's internal scratchpad accumulation**:

1. **AgentExecutor is stateless** - It doesn't use `state["messages"]` directly
2. **But it accumulates in scratchpad** - Each iteration adds:
   - Thought (agent's reasoning)
   - Action (tool call)
   - Observation (tool result) ← **THIS IS THE CULPRIT!**

3. **Tool results can be HUGE:**
   - `list_sprints()` might return 100+ sprints with full details
   - Each sprint: ~500-1000 tokens
   - 100 sprints × 500 tokens = **50,000 tokens** in ONE tool result!

4. **Scratchpad accumulation:**
   - Iteration 1: Thought + Action + Observation (50K tokens)
   - Iteration 2: Previous scratchpad (50K) + New Thought + Action + Observation (50K) = **100K tokens**
   - Iteration 3: Previous scratchpad (100K) + New (50K) = **150K tokens**
   - ...and so on

5. **The entire scratchpad is sent to LLM each iteration:**
   - LangChain's ReAct agent sends the **entire scratchpad** (all previous iterations) to the LLM
   - If you have 5-6 iterations with large tool results, you can easily hit 329K tokens

## Why Browser Reset Doesn't Help

**Browser reset only clears:**
- Frontend state (browser memory)
- Frontend conversation history

**But it DOESN'T clear:**
- ❌ LangGraph state (if checkpointer is enabled)
- ❌ Backend session state
- ❌ Tool results accumulated in agent scratchpad (this is per-request, but accumulates within a single request)

## The Real Problem

**The issue is NOT conversation history** - it's **tool result accumulation within a single request**:

1. User sends: "analyse sprint 10"
2. ReAct agent calls `list_sprints()` → Returns 100 sprints (50K tokens)
3. ReAct agent calls `sprint_report()` → Returns detailed report (20K tokens)
4. ReAct agent calls `burndown_chart()` → Returns chart data (30K tokens)
5. **Total in scratchpad: 100K+ tokens** (and growing with each iteration)

## Solution

We need to **truncate or summarize large tool results** before they're added to the scratchpad:

1. **Truncate tool results** - Limit each observation to a maximum size (e.g., 5K tokens)
2. **Summarize large results** - Use LLM to summarize huge tool results
3. **Limit scratchpad size** - Only keep last N iterations in scratchpad
4. **Better pre-flight check** - Estimate tool result sizes before calling tools

## Next Steps

1. ✅ Added debug logging to see actual token counts in intermediate_steps
2. ⏳ Need to implement tool result truncation
3. ⏳ Need to limit scratchpad accumulation
4. ⏳ Need better pre-flight check that accounts for tool result sizes


