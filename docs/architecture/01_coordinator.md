# Coordinator Node

**Log Prefix:** `[COORDINATOR]`  
**File:** `backend/graph/nodes.py` → `coordinator_node()`

## Purpose
Entry point for all user messages. Routes to appropriate handler.

## Routing Logic

```python
# 1. Check for PM keywords (fast)
pm_keywords = ["sprint", "task", "project", "user", ...]
has_pm_intent = any(kw in message for kw in pm_keywords)

# 2. LLM fallback for multilingual
if not has_pm_intent:
    has_pm_intent = classify_pm_intent_with_llm(message)

# 3. Route
if has_pm_intent:
    goto = "react_agent"  # PM flow
else:
    goto = END  # Conversational response
```

## Debug Logs

| Log Pattern | Meaning |
|-------------|---------|
| `[COORDINATOR-ENTRY]` | Node entered |
| `[COORDINATOR] PM intent detected` | Routing to react_agent |
| `[COORDINATOR] No PM intent` | Routing to END |
| `[COORDINATOR] 🤖 LLM intent` | LLM fallback triggered |

## Common Issues

### Query not routed to PM tools
- **Symptom:** Generic response instead of PM data
- **Check:** Is query detected as PM? See `has_pm_intent` log
- **Fix:** Add keywords or check LLM fallback

### See Also
- [02_intent_detection.md](02_intent_detection.md) - Hybrid detection details
- [03_react_agent.md](03_react_agent.md) - Next step after routing
