# Context Compression: Implemented but NOT Used ❌

## The Issue

Context compression **IS implemented** but **IS NOT USED** in the ReAct agent. The compressed state is created but never passed to the executor.

## Evidence

### 1. Compression IS Implemented ✅

**Code Location:** `src/graph/nodes.py:3126`

```python
# Line 3126: Compression happens
compressed_state = context_manager.compress_messages(state)

# Line 3130-3132: Metadata extracted
optimization_metadata = compressed_state.get("_context_optimization")
if optimization_metadata:
    optimization_messages = _add_context_optimization_tool_call(state, "react_agent", optimization_metadata)

# Line 3134-3137: Results logged
logger.info(
    f"[REACT-AGENT] Context compression: "
    f"original={len(all_messages)} messages, "
    f"compressed={len(compressed_state.get('messages', []))} messages"
)
```

**What happens:**
- ✅ Compression function is called
- ✅ Compressed state is created
- ✅ Compression metadata is extracted
- ✅ Results are logged

### 2. Compression IS NOT USED ❌

**Code Location:** `src/graph/nodes.py:3228`

```python
# Line 3228: Executor is called with ONLY the query string
result = await executor.ainvoke({
    "input": user_query  # Just "analyse sprint 10"
})
```

**What's missing:**
- ❌ `compressed_state` is never passed to `executor.ainvoke()`
- ❌ Compressed messages are never used
- ❌ The executor doesn't know about the compressed context

### 3. The Problem

**LangChain's `AgentExecutor` behavior:**
- When you call `executor.ainvoke({"input": "query"})`, it only receives the input string
- However, the executor might be using conversation history from:
  - The LLM's internal memory/state
  - The full `state["messages"]` that's passed around in LangGraph
  - Previous invocations that stored history

**Result:**
- The executor still uses the **FULL conversation history** (~329K tokens)
- The compressed state (~70K tokens) is created but **completely ignored**
- The system tries to send 329K tokens → gets rate limit error → hangs

## Comparison: Reporter Node (Where It IS Used) ✅

**Code Location:** `src/graph/nodes.py:1529-1552`

```python
# Reporter node DOES use compressed messages
compressed_state = compression_manager.compress_messages({"messages": observation_messages})
compressed_messages = compressed_state.get("messages", [])

# Then it's actually used:
invoke_messages += compressed_messages  # Line 1552
```

**Difference:**
- ✅ Reporter extracts `compressed_messages` from `compressed_state`
- ✅ Reporter uses `compressed_messages` when calling the LLM
- ❌ ReAct agent creates `compressed_state` but never extracts or uses it

## The Fix Needed

### Option 1: Pass Compressed Messages to Executor (If Supported)

```python
# Extract compressed messages
compressed_messages = compressed_state.get("messages", [])

# Pass to executor (if LangChain supports it)
result = await executor.ainvoke({
    "input": user_query,
    "chat_history": compressed_messages  # Use compressed messages
})
```

**Problem:** LangChain's `AgentExecutor` might not support `chat_history` parameter directly.

### Option 2: Create New State with Compressed Messages

```python
# Create a new state with only compressed messages
compressed_messages = compressed_state.get("messages", [])

# Create a minimal state for the executor
minimal_state = {
    "messages": compressed_messages[-5:]  # Only last 5 messages
}

# Use this state when creating the executor
# (This might require modifying how the executor is created)
```

### Option 3: Pre-Flight Token Check (Recommended)

```python
# Before calling executor, check token count
compressed_messages = compressed_state.get("messages", [])
total_tokens = context_manager.count_tokens(compressed_messages, model=model_name)

if total_tokens > model_context_limit * 0.9:  # 90% threshold
    logger.warning(f"Token count ({total_tokens}) too high - escalating to planner")
    return Command(
        update={"escalation_reason": "token_limit_exceeded"},
        goto="planner"
    )

# Only call executor if tokens are within limit
result = await executor.ainvoke({"input": user_query})
```

### Option 4: Use LangChain's Memory System

```python
from langchain.memory import ConversationBufferWindowMemory

# Create memory with window (only keeps last N messages)
memory = ConversationBufferWindowMemory(
    k=5,  # Only keep last 5 messages
    return_messages=True
)

# Pass memory to executor
executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,  # Use memory to limit context
    max_iterations=10,
    ...
)
```

## Summary

| Aspect | Status | Details |
|--------|--------|---------|
| **Compression Implementation** | ✅ Implemented | `compress_messages()` is called |
| **Compression Execution** | ✅ Works | Creates compressed state successfully |
| **Compression Usage** | ❌ **NOT USED** | Compressed state is never passed to executor |
| **Result** | ❌ Fails | System still uses full history → rate limit error |

**Root Cause:** The compressed state is created but **never extracted or used** when calling the executor. The executor continues to use the full conversation history, causing the rate limit error.


