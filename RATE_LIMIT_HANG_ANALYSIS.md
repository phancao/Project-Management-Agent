# Rate Limit Hang Analysis: Why It Gets Stuck

## The Problem

When the system tries to send **329,134 tokens** to `gpt-4o-mini` (which has a **200,000 token limit**), it gets stuck instead of properly escalating to the planner.

## Complete Flow Breakdown

### Step 1: User Query → Coordinator → ReAct Agent

**Input:**
- User query: "analyse sprint 10"
- Full conversation history in `state["messages"]` (potentially 100+ messages)
- Total tokens: ~329K tokens

**Output:**
- Coordinator routes to `react_agent` node
- State passed to `react_agent_node()`

**Code Location:** `src/graph/nodes.py:3053` (`react_agent_node`)

---

### Step 2: ReAct Agent - Context Compression (ATTEMPTED)

**Input:**
- Full state with all messages
- Model context limit: 200K tokens (for gpt-4o-mini)
- ReAct agent budget: 35% = 70K tokens

**Process:**
```python
# Line 3126: Compress the state
compressed_state = context_manager.compress_messages(state)

# Line 3134-3137: Log compression
logger.info(f"Context compression: original={len(all_messages)} messages, compressed={len(compressed_state.get('messages', []))} messages")
```

**Output:**
- `compressed_state` dictionary with compressed messages
- **BUT THIS IS NEVER USED!** ❌

**Code Location:** `src/graph/nodes.py:3103-3138`

---

### Step 3: Create LLM and Agent Executor

**Input:**
- `llm = get_llm_by_type("basic")` (line 3143)
- Tools: PM tools + web_search
- Prompt template

**Process:**
```python
# Line 3211-3215: Create agent
agent = create_react_agent(llm=llm, tools=tools, prompt=react_prompt)

# Line 3217-3224: Create executor
executor = AgentExecutor(
    agent=agent,
    tools=tools,
    max_iterations=10,
    handle_parsing_errors=True,
    return_intermediate_steps=True,
    verbose=True
)
```

**Problem:** 
- The LLM instance is created **WITHOUT** using the compressed state
- LangChain's `AgentExecutor` internally manages conversation history
- The executor might be using the **FULL conversation history** from the state

**Code Location:** `src/graph/nodes.py:3140-3224`

---

### Step 4: Execute ReAct Loop - **WHERE IT GETS STUCK**

**Input:**
```python
# Line 3228: Only passes the query string
result = await executor.ainvoke({
    "input": user_query  # Just "analyse sprint 10"
})
```

**What Actually Happens Inside `executor.ainvoke()`:**

1. **LangChain AgentExecutor internally:**
   - Builds the full prompt with system message
   - **Includes ALL conversation history** (from the LLM's memory/state)
   - Adds tool descriptions
   - Adds agent scratchpad (previous thoughts/actions)

2. **Total tokens sent to OpenAI:**
   - System prompt: ~2K tokens
   - Full conversation history: ~320K tokens ❌
   - Tool descriptions: ~5K tokens
   - Current query: ~10 tokens
   - **TOTAL: ~329K tokens** (exceeds 200K limit!)

3. **OpenAI API Call:**
   ```python
   POST https://api.openai.com/v1/chat/completions
   {
     "model": "gpt-4o-mini",
     "messages": [/* 329K tokens of conversation history */]
   }
   ```

4. **OpenAI Response:**
   ```json
   {
     "error": {
       "message": "Request too large for gpt-4o-mini: Limit 200000, Requested 329134",
       "type": "tokens",
       "code": "rate_limit_exceeded"
     }
   }
   ```

5. **Exception Raised:**
   - `openai.RateLimitError` is raised **INSIDE** `executor.ainvoke()`
   - This is an async call that might be waiting for the HTTP response
   - The exception should propagate up...

**Code Location:** `src/graph/nodes.py:3226-3230`

---

### Step 5: Exception Handling - **WHY IT HANGS**

**Input:**
- `RateLimitError` exception from `executor.ainvoke()`

**Process:**
```python
# Line 3376: Exception caught
except Exception as e:
    logger.error(f"[REACT-AGENT] ❌ Error during execution: {e}", exc_info=True)
    
    # Line 3379-3386: Try to escalate
    return Command(
        update={
            "escalation_reason": f"execution_error: {str(e)}",
            "partial_result": f"Error occurred: {str(e)}",
            "goto": "planner"
        },
        goto="planner"
    )
```

**Why It Gets Stuck:**

1. **The exception IS caught** (line 3376)
2. **The escalation command IS returned** (line 3379-3386)
3. **BUT** - The `executor.ainvoke()` call might be:
   - **Still waiting** for the HTTP response to complete
   - **Hanging** in the async HTTP client
   - **Not properly cancelling** the in-flight request

4. **LangGraph might be waiting** for the node to fully complete before processing the `Command` return

5. **The async context** might not be properly cleaned up, causing the hang

**Code Location:** `src/graph/nodes.py:3376-3386`

---

## Root Causes

### 1. **Compressed State Not Used** ❌
- Context compression happens (line 3126)
- But the compressed messages are **never passed to the executor**
- The executor uses the full conversation history

### 2. **LangChain AgentExecutor Uses Full History** ❌
- `AgentExecutor` internally manages conversation state
- It might be using the LLM's memory or the full state's messages
- No way to pass compressed context to the executor

### 3. **No Pre-Flight Token Check** ❌
- The system doesn't check token count **before** calling the LLM
- It only discovers the problem when OpenAI rejects the request
- By then, the HTTP request is already in flight

### 4. **Async Exception Handling** ⚠️
- The exception is caught, but the underlying HTTP request might still be hanging
- No timeout or cancellation mechanism for stuck requests

---

## Why It Stays Stuck

1. **HTTP Request in Flight:**
   - The OpenAI API call is already sent
   - The async HTTP client is waiting for a response
   - Even though an exception is raised, the connection might not be closed

2. **LangGraph State Machine:**
   - LangGraph might be waiting for the node function to fully complete
   - The `Command` return might not be processed until the async function finishes
   - If the function is stuck waiting, the state machine is stuck

3. **No Timeout:**
   - There's no timeout on the `executor.ainvoke()` call
   - If the HTTP request hangs, the whole system hangs

---

## The Fix Needed

### Option 1: Use Compressed State in Executor (Recommended)

**Problem:** LangChain's `AgentExecutor` doesn't accept compressed messages directly.

**Solution:** Create a custom agent that uses only the compressed messages:

```python
# Instead of passing full state to executor, create a new state with compressed messages
compressed_messages = compressed_state.get("messages", [])

# Create a new agent input with only compressed messages
agent_input = {
    "input": user_query,
    "chat_history": compressed_messages  # Only compressed messages
}

result = await executor.ainvoke(agent_input)
```

### Option 2: Pre-Flight Token Check

**Add token counting BEFORE calling the LLM:**

```python
# Before executor.ainvoke()
total_tokens = estimate_tokens(state["messages"], tools, prompt)
if total_tokens > model_limit:
    logger.warning(f"Token count ({total_tokens}) exceeds limit ({model_limit}) - escalating")
    return Command(update={"escalation_reason": "token_limit_exceeded"}, goto="planner")
```

### Option 3: Add Timeout and Cancellation

**Add timeout to executor call:**

```python
import asyncio

try:
    result = await asyncio.wait_for(
        executor.ainvoke({"input": user_query}),
        timeout=30.0  # 30 second timeout
    )
except asyncio.TimeoutError:
    logger.error("[REACT-AGENT] Timeout - escalating to planner")
    return Command(update={"escalation_reason": "timeout"}, goto="planner")
```

---

## Summary

**The Flow:**
1. ✅ Context compression happens (but not used)
2. ✅ Executor created with full history
3. ❌ Executor tries to send 329K tokens
4. ❌ OpenAI rejects with 429 error
5. ⚠️ Exception caught, but HTTP request hangs
6. ❌ System stuck waiting for response

**The Root Cause:**
- **Compressed state is created but never used**
- **Executor uses full conversation history**
- **No pre-flight token check**
- **No timeout/cancellation mechanism**

**The Fix:**
- Use compressed messages in executor
- Add pre-flight token check
- Add timeout to executor calls
- Properly cancel in-flight requests on error


