# ReAct Agent Debug Guide

## 1. How to Know if ReAct Agent Failed

### Check Backend Logs

Look for these log patterns in `docker logs pm-backend-api`:

#### ✅ ReAct Agent is Running:
```
[REACT-AGENT] 🚀 Starting fast ReAct agent
[REACT-AGENT] 📊 STATUS: ReAct agent is running (check logs for '[REACT-AGENT]' prefix)
[REACT-AGENT] 🔍 Found tool-calling message at index X with N tool calls
[REACT-AGENT] 💭 Extracted thought: ...
```

#### ❌ ReAct Agent Failed (Escalated to Planner):
```
[REACT-AGENT] ⬆️ Too many iterations (N >= 8) - escalating to planner
[REACT-AGENT] ⬆️ Multiple errors detected (N >= 2) - escalating to planner
[REACT-AGENT] ⬆️ Data too large for reporter - escalating to planner
[REACT-AGENT] ❌ Error during execution: ...
[COORDINATOR] 📊 Using full pipeline: escalation=<reason>
```

#### ⚠️ ReAct Agent Never Ran:
```
[COORDINATOR] 📊 Using full pipeline: escalation=, detailed=False
# OR
[COORDINATOR] 🎯 FINAL DECISION: planner
# WITHOUT any [REACT-AGENT] logs
```

### Common Failure Reasons:

1. **Too Many Iterations** (>= 8): Agent is struggling, escalated to planner
2. **Multiple Errors** (>= 2): Tool calls failing repeatedly
3. **Token Limit Exceeded**: Context too large for reporter
4. **Execution Error**: Exception during agent execution
5. **Pre-flight Check Failed**: Context too large before starting

### Frontend Indicators:

- **ReAct Success**: You see "Steps" with tool calls, then "Report" appears
- **ReAct Failed**: You see "Plan" first, then "Steps" from planner → pm_agent → reporter
- **ReAct Never Ran**: No "Steps" section, only "Plan" and "Report"

---

## 2. Why Thoughts/Reasoning Aren't Showing

### Root Cause

LangGraph's `create_react_agent` uses **structured tool calling**, not text-based ReAct format. This means:
- AIMessage `content` is often **empty** when using structured tool calls
- Reasoning is stored in `additional_kwargs.reasoning_content` (if model supports it)
- The LLM doesn't generate "Thought: ..." text format

### Current Implementation

The code now tries **3 methods** to extract thoughts:

1. **Method 1**: Check `additional_kwargs.reasoning_content` (LangGraph/OpenAI format)
2. **Method 2**: Check AIMessage `content` for "Thought:" pattern (text-based ReAct)
3. **Method 3**: Generate fallback thought based on tool being called

### Debug Steps

1. **Check if ReAct is running**:
   ```bash
   docker logs pm-backend-api | grep "REACT-AGENT"
   ```

2. **Check if thoughts are extracted**:
   ```bash
   docker logs pm-backend-api | grep "💭"
   ```

3. **Check message structure**:
   Look for logs like:
   ```
   [REACT-AGENT] 🔍 Message X: type=AIMessage, has_tool_calls=True, content_len=0, reasoning_content=False
   ```

### Why Thoughts Might Still Not Show

1. **Model doesn't support reasoning_content**: Not all models (e.g., gpt-3.5-turbo) support `reasoning_content` in `additional_kwargs`
2. **Structured tool calling**: When using structured tool calls, the LLM doesn't generate text-based "Thought:" format
3. **Content is empty**: AIMessage content is empty when only tool calls are present

### Solution Options

**Option A: Use a model with reasoning support** (e.g., o1-preview, o3-mini)
- These models explicitly support reasoning tokens

**Option B: Modify prompt to force reasoning**
- Add explicit instruction: "Before calling a tool, explain your reasoning in the message content"

**Option C: Use fallback thoughts** (already implemented)
- Generate thoughts based on tool names: "I need to use list_sprints to answer the user's question"

**Option D: Use text-based ReAct format** (not recommended)
- Switch back to text-based ReAct, but lose structured tool calling benefits

---

## Quick Debug Commands

```bash
# Check if ReAct ran
docker logs pm-backend-api --tail 500 | grep -E "REACT-AGENT|COORDINATOR.*routing|ADAPTIVE"

# Check for thoughts
docker logs pm-backend-api --tail 500 | grep "💭"

# Check for escalations
docker logs pm-backend-api --tail 500 | grep "⬆️\|escalat"

# Check message structure
docker logs pm-backend-api --tail 500 | grep "Message.*type="
```


