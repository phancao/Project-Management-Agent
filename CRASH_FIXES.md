# Backend Crash Fixes ✅

## Issues Found & Fixed

### Issue 1: Token Check Function Call Error ❌

**Error:**
```
[REACT-AGENT] Token check failed: ContextManager._count_tokens_with_tiktoken() 
missing 2 required positional arguments: 'messages' and 'model'
```

**Root Cause:**
Called `ContextManager._count_tokens_with_tiktoken([...])` but it's a **static method** that requires `messages` AND `model` parameters.

**Fix:**
Replaced with simple character-based estimation (1 token ≈ 4 chars):
```python
# OLD (BROKEN):
output_tokens = ContextManager._count_tokens_with_tiktoken([
    {"role": "assistant", "content": output}
])

# NEW (FIXED):
output_tokens = len(output) // 4  # Rough estimate: 1 token ≈ 4 chars
```

---

### Issue 2: AIMessage Attribute Error ❌

**Error:**
```
AttributeError: 'AIMessage' object has no attribute 'tool_call_chunks'
```

**Root Cause:**
When processing non-chunked `AIMessage`, the code checked `message_chunk.tool_call_chunks` directly, but `AIMessage` doesn't have this attribute (only `AIMessageChunk` does).

**Fix:**
Used `getattr()` with default `None` to safely check for attributes:

```python
# OLD (BROKEN):
has_chunks = bool(message_chunk.tool_call_chunks) if hasattr(message_chunk, 'tool_call_chunks') else False
# ...
elif message_chunk.tool_call_chunks:  # ← Crashes if attribute doesn't exist!

# NEW (FIXED):
has_chunks = bool(getattr(message_chunk, 'tool_call_chunks', None))
# ...
elif getattr(message_chunk, 'tool_call_chunks', None):  # ← Safe!
```

**Applied to 3 locations:**
1. Initial check: `has_tool_calls = bool(getattr(message_chunk, 'tool_calls', None))`
2. Initial check: `has_chunks = bool(getattr(message_chunk, 'tool_call_chunks', None))`
3. Condition: `elif getattr(message_chunk, 'tool_call_chunks', None):`

---

## Files Changed

### 1. `src/graph/nodes.py` (react_agent_node)
**Line ~3110:** Token estimation logic
- Removed broken `ContextManager._count_tokens_with_tiktoken()` call
- Added simple character-based estimation

### 2. `backend/server/app.py` (_process_message_chunk)
**Lines ~566-605:** AIMessage/AIMessageChunk handling
- Changed `hasattr()` + direct access to `getattr()` with defaults
- Applied to `tool_calls` and `tool_call_chunks` checks

---

## Why These Errors Caused "Stuck" Behavior

### The Crash Sequence

1. **ReAct completes** → Returns `AIMessage` with result
2. **Backend tries to stream** → Calls `_process_message_chunk()`
3. **Token check fails** → Warning logged, but continues
4. **AIMessage processing crashes** → `AttributeError: 'tool_call_chunks'`
5. **Exception handler catches** → Logs error
6. **Stream terminates** → Frontend never gets final message!

**Result:** Frontend shows spinner forever (no error, no result)

---

## Expected Behavior Now

### Scenario 1: Small Data (Fast Path)
```
[REACT-AGENT] Token check: output=350, state=200, total=550, reporter_limit=13927
[REACT-AGENT] ✅ Success - returning answer (88 chars)
[BACKEND] 📨 messages stream: type=AIMessage
[BACKEND] ✅ Added finish_reason for non-chunked AIMessage: stop
[FRONTEND] ✅ Displays result
```

### Scenario 2: Large Data (Escalation)
```
[REACT-AGENT] Token check: output=12000, state=2500, total=14500, reporter_limit=13927
[REACT-AGENT] ⬆️ Data too large - escalating to full pipeline
[PLANNER] Creating multi-step plan...
[PM_AGENT] Executing steps...
[REPORTER] ✅ Success!
```

### Scenario 3: Token Check Fails (Graceful Fallback)
```
[REACT-AGENT] Token check failed: <some error>
[REACT-AGENT] ✅ Success - returning answer (88 chars)  ← Still works!
[BACKEND] 📨 messages stream: type=AIMessage
[BACKEND] ✅ Added finish_reason for non-chunked AIMessage: stop
[FRONTEND] ✅ Displays result
```

---

## Test It! 🚀

**Try: "analyse sprint 5"**

**Before fixes:**
```
Frontend: "Analyzing..." ← Stuck forever
Logs: AttributeError: 'AIMessage' object has no attribute 'tool_call_chunks'
```

**After fixes:**
```
Frontend: ✅ Shows result OR escalates to full pipeline
Logs: No crashes, clean execution
```

---

## Summary

✅ **Fixed:** Token check function call (wrong arguments)
✅ **Fixed:** AIMessage attribute access (safe getattr)
✅ **Result:** Backend no longer crashes when processing ReAct results
✅ **UX:** Frontend always gets a response (no more stuck spinner)

**Key lesson:** When handling multiple message types (AIMessage vs AIMessageChunk), always use `getattr()` with defaults instead of direct attribute access!


