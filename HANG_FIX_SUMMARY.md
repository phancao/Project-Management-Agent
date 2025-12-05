# Server Hang Fix ✅

## Problem

**User said:** "Server hang again. It should throw some error or message to user"

**What was happening:**
- Backend completed in 5.17 seconds ✅
- Reporter detected context overflow ✅
- Reporter returned error message ✅
- **BUT frontend showed "Generating insights..." forever** ❌
- User saw nothing - looked like the server was stuck

---

## Root Cause

The reporter was returning a **non-chunked `AIMessage`** (error message), but the backend's `_process_message_chunk` function only handled `AIMessageChunk` objects!

### The Flow

1. **Reporter node** returns error message:
```python
# src/graph/nodes.py (line 1544-1554)
error_ai_message = AIMessage(
    content=error_message,
    name="reporter",
    response_metadata={"finish_reason": "stop", "error_type": "context_too_large"}
)

return {
    "messages": [error_ai_message],  # AIMessage (not AIMessageChunk!)
    "final_report": error_message,
}
```

2. **Backend logs** (11:28:25):
```
[REPORTER] ERROR: Final token count (21492) exceeds limit. Cannot generate report
[BACKEND] 📨 messages stream: type=AIMessage  ← Non-chunked message!
[BACKEND] ✅ Task completed: reporter
[BACKEND] Total response time: 5.17s
```

3. **Backend `_process_message_chunk`** (backend/server/app.py:566):
```python
# ❌ OLD CODE - Only handled AIMessageChunk
elif isinstance(message_chunk, AIMessageChunk):
    # ... process chunk
    yield _make_event("message_chunk", event_stream_message)
# ❌ AIMessage falls through - NO HANDLER!
```

4. **Frontend** (web/src/core/messages/merge-message.ts:28-30):
```typescript
// Only sets isStreaming=false when finish_reason is received
if (event.data.finish_reason) {
  message.finishReason = event.data.finish_reason;
  message.isStreaming = false;  // ← Never called!
}
```

**Result:** Message was sent but **WITHOUT `finish_reason`**, so frontend kept showing "Generating insights..." forever!

---

## The Fix

### Updated `_process_message_chunk` to handle both `AIMessageChunk` AND `AIMessage`

```python
# backend/server/app.py (line 566-569)

# ✅ NEW: Handle BOTH AIMessageChunk and AIMessage
elif isinstance(message_chunk, (AIMessageChunk, AIMessage)):
    is_chunk = isinstance(message_chunk, AIMessageChunk)
    has_tool_calls = bool(message_chunk.tool_calls) if hasattr(message_chunk, 'tool_calls') else False
    has_chunks = bool(message_chunk.tool_call_chunks) if hasattr(message_chunk, 'tool_call_chunks') else False
    logger.debug(
        f"Processing {'AIMessageChunk' if is_chunk else 'AIMessage'}, "
        f"tool_calls={has_tool_calls}, tool_call_chunks={has_chunks}"
    )
```

### Added `finish_reason` for non-chunked messages

```python
# backend/server/app.py (line 661-675)

# ✅ NEW: For non-chunked AIMessage, ensure finish_reason is set
if not is_chunk and not event_stream_message.get("finish_reason"):
    # Extract finish_reason from response_metadata if available
    if hasattr(message_chunk, 'response_metadata') and message_chunk.response_metadata:
        event_stream_message["finish_reason"] = message_chunk.response_metadata.get("finish_reason", "stop")
    else:
        event_stream_message["finish_reason"] = "stop"
    logger.info(
        f"✅ Added finish_reason for non-chunked AIMessage: "
        f"{event_stream_message.get('finish_reason')}, "
        f"message_id: {event_stream_message.get('id')}, "
        f"agent: {event_stream_message.get('agent')}"
    )
```

---

## Expected Behavior Now

**Try: "analyse sprint 5"**

### Scenario: Context Too Large (Current Issue)

**Before fix:**
```
[11:28:25] Backend: Final token count (21492) exceeds limit
[11:28:25] Backend: ✅ Task completed: reporter (5.17s)
Frontend: "Generating insights..." ← STUCK FOREVER ❌
```

**After fix:**
```
[Time] Backend: Final token count (21492) exceeds limit
[Time] Backend: 📨 messages stream: type=AIMessage
[Time] Backend: ✅ Added finish_reason for non-chunked AIMessage: stop
[Time] Backend: ✅ Task completed: reporter (5.17s)

Frontend displays:
┌─────────────────────────────────────────────────┐
│ ❌ Context Too Large                            │
│                                                 │
│ The analysis data (21,492 tokens) exceeds the  │
│ model's limit (16,385 tokens).                  │
│                                                 │
│ Current model: gpt-3.5-turbo (max 16,385)      │
│                                                 │
│ Solutions:                                      │
│ 1. ✅ Switch to a larger model:                 │
│    - GPT-4o (128,000 tokens)                    │
│    - Claude 3.5 Sonnet (200,000 tokens)         │
│    - DeepSeek (64,000 tokens)                   │
│                                                 │
│ 2. Request a more focused analysis              │
│ 3. Reduce the number of sprints/tasks           │
└─────────────────────────────────────────────────┘
```

**Result:** ✅ User sees error in ~5 seconds (not hung)

---

## Files Changed

1. ✅ `backend/server/app.py`
   - Updated `_process_message_chunk` to handle both `AIMessageChunk` and `AIMessage`
   - Added `finish_reason` extraction for non-chunked messages
   
2. ✅ `src/graph/nodes.py` (already fixed in previous commit)
   - Reporter returns user-friendly error message instead of crashing

---

## What This Fixes

1. **✅ Reporter error messages now display immediately** (5-7 seconds)
2. **✅ Frontend knows when message is complete** (via `finish_reason`)
3. **✅ No more infinite "Generating insights..."**
4. **✅ Works for ANY non-chunked AIMessage** (not just errors)

---

## Test It Now! 🚀

**Try:** "analyse sprint 5"

**You should see:**
- ✅ Backend completes in ~5 seconds
- ✅ Error message displays (with model upgrade suggestions)
- ✅ No hanging or stuck spinner

**Or switch to GPT-4o/Claude and it should work!** 🎯


