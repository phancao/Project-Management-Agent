# PM Intent Detection Fix Plan

## Problem Statement

**Issue**: Simple greetings like "hi" are incorrectly triggering "🦌 Starting DeerFlow research..." message, indicating they're being detected as PM-related queries when they should be handled conversationally.

**Expected Behavior**:
- "hi", "hello", "hey" → Should respond conversationally (no "Starting research" message, no analysis box)
- "list sprints", "show tasks" → Should show "Starting research" message and route to ReAct agent

## Root Cause Analysis

### Current Implementation

1. **Server-side detection** (`src/server/app.py` line 3297-3321):
   - Checks PM keywords before sending "Starting research" message
   - Keywords: `["sprint", "task", "project", "user", "epic", "backlog", "burndown", "velocity", "assign", "assignee", "team member", "work package", "version", "milestone", "status", "priority", "due date", "story point", "scrum", "kanban", "board", "list", "show", "get", "analyze", "report", "health", "dashboard"]`
   - Logic: `any(keyword in user_message_lower for keyword in pm_keywords)`

2. **Coordinator detection** (`src/graph/nodes.py` line 988-990):
   - Same keyword list and logic
   - Routes to ReAct agent if PM intent detected
   - Routes to END (conversational) if no PM intent

### Investigation Findings

- ✅ "hi" does NOT match any PM keywords (verified with Python test)
- ❌ Logs show: `[PM-CHAT] 📊 PM intent detected: 'hi'` (incorrect detection)
- ❓ Need to check: Why is "hi" being detected as PM intent?

### Possible Causes

1. **Substring matching issue**: "hi" might be matching "health" or another keyword
2. **Message extraction issue**: `user_message` might contain more than just "hi"
3. **Case sensitivity or whitespace issue**: Message might have extra characters
4. **Different code path**: Detection might be happening elsewhere

## Debug Logging Added

Added debug logging in `src/server/app.py` (line 3303-3307):
```python
if user_message_lower in ["hi", "hello", "hey"]:
    matching_keywords = [kw for kw in pm_keywords if kw in user_message_lower]
    logger.warning(f"[PM-CHAT] 🔍 DEBUG: user_message_lower='{user_message_lower}', has_pm_intent={has_pm_intent}, matching_keywords={matching_keywords}")
```

## Root Cause Found ✅

**Issue**: The coordinator was extracting the message content incorrectly. The message content included project_id context (e.g., "hi\n\nproject_id: d7e300c6..."), which caused "project" keyword to match, triggering PM intent detection.

**Evidence from logs**:
```
[COORDINATOR] 📊 PM intent detected: 'hi

project_id: d7e300c6-d6c0-4c08-bc8d-e41967458d...' - routing to ReAct agent
```

## Fix Applied ✅

**File**: `src/graph/nodes.py` (lines 978-1003)

**Changes**:
1. **Find last HumanMessage**: Instead of just taking the last message, now finds the last `HumanMessage` to ensure we get the actual user message
2. **Extract first line only**: Uses `user_message.split('\n')[0]` to extract only the first line, preventing context/metadata from being included in PM intent detection
3. **Added debug logging**: Logs debug info when greeting messages are detected

**Code**:
```python
# Find the last HumanMessage (user message), not just the last message
from langchain_core.messages import HumanMessage
for msg in reversed(messages_list):
    if isinstance(msg, HumanMessage) or (isinstance(msg, dict) and msg.get('type') == 'human'):
        if hasattr(msg, 'content'):
            user_message = str(msg.content).strip().lower()
        elif isinstance(msg, dict) and 'content' in msg:
            user_message = str(msg['content']).strip().lower()
        break

# Extract only the first line (user's actual message) to avoid matching context/metadata
user_message_first_line = user_message.split('\n')[0].strip()

# PM intent detection uses first line only
has_pm_intent = any(keyword in user_message_first_line for keyword in pm_keywords)
```

## Test Results ✅

- [x] Test with "hi" → ✅ Works! Responds conversationally without "Starting research"
- [ ] Test with "hello" → Need to test
- [ ] Test with "list sprints" → Need to test
- [ ] Test with "show tasks" → Need to test

## Additional Issue Found: ReAct Being Skipped

**Problem**: After ReAct escalates to planner, `previous_result` and `routing_mode` persist in state. On the next PM query, the adaptive routing logic sees these values and routes directly to planner, skipping ReAct entirely.

**Root Cause**: 
- When ReAct escalates, it doesn't clear `previous_result` and `routing_mode` from state
- When a new PM query comes in, if `previous_result` and `routing_mode == "react_first"` exist, the adaptive routing logic checks if user needs escalation
- If `detect_user_needs_more_detail` returns True (which it might for any PM query), it routes directly to planner, skipping ReAct

**Fix Applied**:
1. **Clear state when ReAct escalates** (line 5595-5604): Clear `previous_result` and `routing_mode` when ReAct escalates to planner
2. **Clear state for new PM queries** (line 1050-1057): Clear `previous_result` and `routing_mode` for new PM queries to ensure ReAct is always called first
3. **Clear state after user escalation** (line 966): Clear `previous_result` after user escalation to prevent state from persisting

**Code Changes**:
```python
# When ReAct escalates (line 5595-5604)
return Command(
    update={
        "escalation_reason": escalation_reason,
        "react_attempts": intermediate_steps if intermediate_steps else [],
        "react_thoughts": thoughts if 'thoughts' in locals() else [],
        "partial_result": output if output else "",
        "previous_result": None,  # Clear previous_result when escalating
        "routing_mode": "",  # Clear routing_mode when escalating
        "goto": "planner"
    },
    goto="planner"
)

# For new PM queries (line 1050-1057)
return Command(
    update={
        "locale": state.get("locale", "en-US"),
        "research_topic": state.get("research_topic", ""),
        "previous_result": None,  # Clear previous_result for new PM queries
        "routing_mode": "",  # Clear routing_mode for new PM queries
        "goto": "react_agent"
    },
    goto="react_agent"
)
```

**Result**: New PM queries will now always go through ReAct first, and only escalate to planner if ReAct fails or the user explicitly requests more detail.

## Revert Strategy

If fix doesn't work:
1. Revert changes to `src/server/app.py` (remove debug logging if not useful)
2. Revert changes to `src/graph/nodes.py` (if any)
3. Check logs for next approach
4. Try alternative solution

## Notes

- Debug logging should be kept if it's useful for tracking the issue
- Both server and coordinator use the same keyword list - ensure they stay in sync
- Consider creating a shared constant for PM keywords to avoid duplication

