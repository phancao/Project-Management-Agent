# SSE Streaming Pipeline

**Log Prefix:** `[STREAM-Q]`  
**File:** `backend/server/app.py` → `stream_thread_updates()`

## Purpose
Real-time delivery of tool results and messages to frontend via Server-Sent Events.

## Architecture

```
Tool Execution
     ↓
asyncio.Queue (per thread)
     ↓
SSE Generator
     ↓
Frontend EventSource
```

## Key Components

| Component | File | Purpose |
|-----------|------|---------|
| Queue Registry | `app.py` | Thread-specific queues |
| `get_tool_result_queue()` | `app.py` | Get/create queue |
| `on_tool_result_callback` | `nodes.py` | Push to queue |
| SSE drain loop | `app.py` | Yield events |

## Event Types

| Event | Content |
|-------|---------|
| `tool_call_result` | Tool execution result |
| `message` | LLM response chunk |
| `pm_agent_thinking` | Agent reasoning |

## Debug Logs

| Log Pattern | Meaning |
|-------------|---------|
| `Queue: pushing tool result` | Result added to queue |
| `Queue: draining` | SSE checking for events |
| `Queue: emitting` | Event sent to frontend |

## Common Issues

### Results not streaming
- **Symptom:** Results appear only at end
- **Check:** Queue being populated
- **Fix:** Verify `on_tool_result_callback` is called

### Wrong thread
- **Symptom:** Results go to wrong user
- **Check:** `thread_id` in config
- **Fix:** Ensure correct thread_id passed to callback

## See Also
- [03_react_agent.md](03_react_agent.md) - Where tool results originate
