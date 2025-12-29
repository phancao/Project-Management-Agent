# Streaming Issues

Common issues with SSE event delivery.

## Results Not Streaming (Batch Delivery)

### Symptoms
- Tool results appear only at end
- Long "waiting" state
- No real-time updates

### Check
```
Look for: [STREAM-Q] Queue: pushing tool result
Expected: Should appear immediately after tool execution
```

### Causes & Fixes

| Cause | Fix |
|-------|-----|
| Callback not invoked | Verify `on_tool_result_callback` called in `_act()` |
| Wrong thread_id | Check `thread_id` from `config.configurable` |
| Queue not drained | Check SSE loop is draining queue |

---

## Wrong User Receives Events

### Symptoms
- User sees another user's data
- Events appear in wrong thread

### Check
```
Look for: thread_id in callback logs
```

### Fix
- Queue registry uses `thread_id` as key
- Ensure correct `thread_id` passed from config

---

## Events Missing

### Symptoms
- Some tool results don't appear
- Partial data in UI

### Check
```
Look for: [STREAM-Q] Queue: emitting
Count: Should match number of tool calls
```

### Fix
- Check if exceptions interrupt callback
- Verify all tools call the callback

---

## Frontend Not Receiving

### Symptoms
- Backend logs show events sent
- UI doesn't update

### Check
- Browser DevTools → Network → EventSource
- Look for SSE connection

### Fix
- Check CORS headers
- Verify SSE endpoint responding
