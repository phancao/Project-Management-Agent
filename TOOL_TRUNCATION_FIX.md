# Tool Output Truncation Fix - Context Optimizer Now Works for ReAct Agent

## The Problem

**User reported:** "then the context optimizer is not working"

**Root cause:** The context optimizer compresses `state["messages"]`, but the ReAct agent's scratchpad is managed internally by LangChain's `AgentExecutor` and accumulates tool results separately. Large tool results (e.g., 50K tokens from `list_sprints()`) were being added directly to the scratchpad without truncation, causing 329K token accumulation.

## The Solution

**Wrap all tools to truncate their outputs** before they're returned to the AgentExecutor, preventing large tool results from accumulating in the scratchpad.

### Implementation

1. **Tool Wrapping Function:**
   ```python
   def wrap_tool_with_truncation(tool: BaseTool, max_tokens: int = 5000) -> BaseTool:
       """Wrap a tool to truncate its output to prevent token overflow in scratchpad."""
       # Detects if tool is async or sync
       # Wraps the tool function to truncate results > 5000 tokens (20K chars)
       # Uses sanitize_tool_response() for smart truncation (preserves JSON structure)
   ```

2. **Applied to All ReAct Agent Tools:**
   - PM tools (list_sprints, sprint_report, etc.)
   - Web search tool
   - All tools are wrapped before being passed to AgentExecutor

3. **Truncation Strategy:**
   - Max 5,000 tokens per tool result (20,000 chars)
   - Uses `sanitize_tool_response()` which:
     - Compresses large JSON arrays (keeps first 20 items)
     - Preserves JSON structure
     - Truncates intelligently (not just cutting off mid-sentence)

## How It Works

**Before (Broken):**
```
Tool: list_sprints() → Returns 50K tokens
  ↓
AgentExecutor adds to scratchpad: 50K tokens
  ↓
Next iteration: Previous scratchpad (50K) + New tool result (50K) = 100K tokens
  ↓
After 5-6 iterations: 329K tokens ❌
```

**After (Fixed):**
```
Tool: list_sprints() → Returns 50K tokens
  ↓
Tool wrapper truncates to 5K tokens
  ↓
AgentExecutor adds to scratchpad: 5K tokens
  ↓
Next iteration: Previous scratchpad (5K) + New tool result (5K) = 10K tokens
  ↓
After 5-6 iterations: ~30K tokens ✅ (well under limit)
```

## Benefits

1. **Prevents scratchpad overflow** - Tool results are capped at 5K tokens each
2. **Preserves JSON structure** - Smart truncation maintains data integrity
3. **Compresses arrays** - Large lists are compressed to first 20 items
4. **Works for all tools** - Both async and sync tools are wrapped correctly

## Testing

Test with:
```
analyse sprint 10
```

**Expected behavior:**
- Tools return truncated results (max 5K tokens each)
- Scratchpad stays under 30K tokens total
- No more 329K token errors
- Context optimizer now effectively prevents token overflow

## Files Changed

- `src/graph/nodes.py` - Added tool wrapping in `react_agent_node()`
- Uses existing `sanitize_tool_response()` from `src/utils/json_utils.py`


