# Testing Thought Extraction Fix

## What to Test

1. **Thoughts come from agent reasoning** (not plan descriptions)
2. **Thoughts match actual tool calls** (e.g., if agent calls `list_user`, thought should be about `list_user`)
3. **Thoughts appear before tool calls** (correct order: Thought → Tool Call → Result)

## Quick Test

### Option 1: Manual Browser Test
1. Open: http://localhost:3000
2. Navigate to PM Chat
3. Ask: **"list all users in this project"**
4. Observe: Thoughts should appear before tool calls

### Option 2: Monitor Logs While Testing
In a terminal, run:
```bash
/tmp/test_thought_fix_monitor.sh
```

Then in browser, ask: **"list all users in this project"**

Watch the logs for:
- `💭 Extracted thought from...` messages
- Which tool is being called
- Whether thought matches the tool

## Test Steps

### 1. Open Browser
- Navigate to: http://localhost:3000
- Go to PM Chat interface

### 2. Test Query
Ask: **"list all users in this project"** or **"show me all users"**

### 3. What to Look For

#### ✅ Expected Behavior:
- **Thought appears FIRST** (before tool call)
- **Thought matches the tool**: If agent calls `list_user`, thought should say something about listing users, NOT about `list_projects`
- **Thought comes from agent reasoning**: Should reflect what agent is actually thinking, not generic plan description

#### ❌ If You See:
- Thought says "Use list_projects()" but agent calls `list_user` → **FIX NOT WORKING**
- Thought appears AFTER tool call → **Ordering issue**
- No thought at all → **Agent not writing reasoning or extraction failing**

### 4. Check Logs

While testing, monitor logs:
```bash
# Terminal 1: Watch backend logs
tail -f logs/backend.log | grep -E "(pm_agent|thought|Extracted|reasoning|list_user)" -i

# Terminal 2: Watch server logs  
tail -f logs/server.log | grep -E "(pm_agent|thought|Extracted|reasoning)" -i
```

### 5. Expected Log Messages

Look for these log messages:
- `💭 Extracted thought from reasoning_content:` (if model supports it)
- `💭 Extracted thought from content (Thought: prefix):` (if agent writes "Thought:")
- `💭 Extracted thought from content (before action):` (if agent writes reasoning before action)
- `⚠️ No agent reasoning found, using plan step description as fallback` (should be rare)

### 6. If Agent Doesn't Write Reasoning

If you see the warning about using plan step description as fallback:
- The agent prompt requires reasoning, but agent may not be following it
- Check if agent is using structured tool calling (content may be empty)
- May need to adjust prompt or use a model that supports reasoning_content

## Debugging

### Check Agent Response
Look in logs for:
```
[pm_agent] Message X: AIMessage with Y tool calls: [list_user]
[pm_agent] 💭 Extracted thought from content: ...
```

### Check What Agent Actually Wrote
The logs should show:
- Agent's message content (if any)
- Whether reasoning_content exists
- What thought was extracted

## Success Criteria

✅ **Fix is working if:**
1. Thought appears before tool call
2. Thought matches the actual tool being called
3. Thought reflects agent's reasoning (not generic plan description)
4. Logs show "Extracted thought from content" or "Extracted thought from reasoning_content"

❌ **Fix needs more work if:**
1. Thought still comes from plan description (logs show "using plan step description as fallback")
2. Thought doesn't match tool call
3. Thought appears after tool call
4. No thought appears at all

