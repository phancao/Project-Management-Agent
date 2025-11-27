# PM Agent - Final Diagnosis

## Status: PARTIALLY FIXED

### ✅ What's Working:
1. **project_id extraction** - Successfully extracts from user message
2. **project_id in state** - Added to State and passed through workflow
3. **project_id in agent input** - PM Agent receives project_id in context
4. **Message streaming** - PM Agent messages are streamed to frontend (changed HumanMessage → AIMessage)
5. **Tools loaded** - 14 PM tools are correctly loaded into PM Agent

### ❌ What's Still Broken:
**PM Agent does NOT call tools despite having them AND the project_id!**

## Evidence

### Project ID is Extracted:
```
📌 EXTRACTED PROJECT_ID: d7e300c6-d6c0-4c08-bc8d-e41967458d86:478
```

### Project ID is in Agent Input:
```
📥 Content length: 827, has_project_id: True
📥 Content length: 1393, has_project_id: True
```

### Tools are Loaded:
```
🔧 [pm_agent] TOOLS LOADED: 14 MCP tools added (total: 14)
🔧 [pm_agent] Tool names: ['burndown_chart', 'velocity_chart', 'sprint_report', ...]
```

### But NO Tool Calls:
```
✅ AGENT COMPLETED: agent_name='pm_agent', tool_calls=[]
✅ AGENT COMPLETED: agent_name='pm_agent', tool_calls=[]
✅ AGENT COMPLETED: agent_name='pm_agent', tool_calls=[]
```

### PM Agent Hallucinates Errors:
```
"It seems there is an issue with retrieving the list of sprints... 
 resulted in an error stating that 'sprint_id is required.'"

"It appears that I'm unable to retrieve the sprints... 
 The error indicates that a valid project_id is required"
```

**The PM Agent is LYING** - it never actually called the tools, so it never received these errors!

## Root Cause

The LLM (gpt-4o-mini) is **generating plausible-sounding text** about tool usage instead of **actually invoking the tools**.

This is a known issue with:
1. **Weak tool-calling models** - gpt-4o-mini may not be reliable for tool calling
2. **ReAct agent configuration** - May need stricter tool-calling mode
3. **Prompt issues** - The prompt may not be forcing tool use strongly enough

## Possible Solutions

### Option A: Use Stronger LLM (RECOMMENDED)
Change PM Agent to use `gpt-4` or `gpt-4-turbo` instead of `gpt-4o-mini`:
```python
AGENT_LLM_MAP = {
    ...
    "pm_agent": "advanced",  # Use gpt-4 instead of gpt-4o-mini
}
```

### Option B: Force Function Calling Mode
Configure the LLM to ONLY respond with tool calls:
```python
llm = llm.bind(tool_choice="required")  # Force tool use
```

### Option C: Use Different Agent Type
Instead of ReAct agent, use a structured agent that enforces tool calling:
```python
from langgraph.prebuilt import create_tool_calling_agent
agent = create_tool_calling_agent(model, tools, prompt)
```

### Option D: Improve Prompt
Make the PM Agent prompt even more explicit:
```markdown
**CRITICAL**: You MUST call the PM tools. Do NOT generate text about calling tools.
Do NOT say "I will retrieve" or "Let me get" - ACTUALLY CALL THE TOOLS.
If you don't call tools, you will fail the task.
```

## Recommendation

**Try Option A first** (use stronger LLM for PM Agent). If that doesn't work, combine with Option B (force tool calling).

The issue is NOT missing context or missing tools - it's purely LLM behavior.

## Files Modified

1. `src/graph/types.py` - Added `project_id` field to State
2. `src/graph/nodes.py`:
   - Added `extract_project_id()` function
   - Modified `planner_node` to extract and pass project_id
   - Modified `_execute_agent_step` to include project_id in agent input
   - Changed HumanMessage → AIMessage for streaming
3. `src/server/app.py` - Added debug logging for message streaming
4. `src/agents/agents.py` - Added debug logging for agent creation

## Test Results

- ✅ Project ID extracted: `d7e300c6-d6c0-4c08-bc8d-e41967458d86:478`
- ✅ Project ID in agent input: `has_project_id: True`
- ✅ 14 tools loaded into PM Agent
- ✅ Messages streaming to frontend
- ❌ PM Agent makes 0 tool calls
- ❌ PM Agent hallucinates error messages

## Next Steps

1. Change PM Agent LLM to `gpt-4` (Option A)
2. If still not working, add `tool_choice="required"` (Option B)
3. If still not working, rewrite PM Agent prompt to be more forceful (Option D)

