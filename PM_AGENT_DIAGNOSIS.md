# PM Agent Diagnosis - Complete Analysis

## Executive Summary

The PM Agent has been successfully integrated into the workflow, but it has **TWO CRITICAL ISSUES**:

1. ✅ **FIXED**: Messages weren't being streamed to frontend (changed HumanMessage → AIMessage)
2. ❌ **STILL BROKEN**: PM Agent doesn't call tools despite having them

## Issue #1: Messages Not Streaming (FIXED)

### Root Cause
In `src/graph/nodes.py` line 982, PM Agent responses were wrapped in `HumanMessage`:
```python
HumanMessage(content=response_content, name=agent_name)  # ❌ Wrong!
```

The streaming code only streams `AIMessage` objects.

### Fix Applied
Changed to `AIMessage`:
```python
AIMessage(content=response_content, name=agent_name)  # ✅ Correct!
```

### Verification
Debug logs confirm streaming is working:
```
✨ STREAMING MESSAGE: node_name='pm_agent', content_len=150
✨ STREAMING MESSAGE: node_name='pm_agent', content_len=227
✨ STREAMING MESSAGE: node_name='pm_agent', content_len=328
```

## Issue #2: PM Agent Doesn't Use Tools (STILL BROKEN)

### What We Know

#### ✅ Tools ARE Loaded
```
🔧 [pm_agent] TOOLS LOADED: 14 MCP tools added (total: 14)
🔧 [pm_agent] Tool names: ['burndown_chart', 'velocity_chart', 'sprint_report', 
    'project_health', 'list_projects', 'get_project', 'list_tasks', 'get_task', 
    'create_task', 'update_task', 'list_sprints', 'get_sprint', 'list_epics', 'get_epic']
```

#### ✅ Agent IS Created With Tools
```
🤖 CREATE_AGENT: name='pm_agent', type='pm_agent', tools_count=14, template='pm_agent'
```

#### ✅ Agent IS Invoked
```
🎯 INVOKING AGENT: agent_name='pm_agent', step='Retrieve Sprint 4 Details'
```

#### ❌ Agent Makes NO Tool Calls
```
✅ AGENT COMPLETED: agent_name='pm_agent', tool_calls=[]
```

### What PM Agent Says (But Doesn't Do)

The PM Agent generates responses that CLAIM it will use tools:
- "Let me retrieve Sprint 4 data from the PM system."
- "Let's proceed to retrieve the details of Sprint 4 tasks..."
- "Let me proceed with analyzing the metrics for Sprint 4..."

**But it never actually calls the tools!**

### Root Cause Analysis

The LLM (gpt-4o-mini) is generating TEXT about using tools instead of generating TOOL CALLS. This happens because:

1. **Missing Context**: The `project_id` is stripped from the plan title
   - User input: "Analyze Sprint 4\n\nproject_id: d7e300c6-d6c0-4c08-bc8d-e41967458d86:478"
   - Plan title: "Sprint 4 Performance Analysis" (project_id missing!)
   - Agent receives: "# Research Topic\n\nSprint 4 Performance Analysis\n\n# Current Step..."

2. **LLM Behavior**: Without the project_id, the LLM doesn't know which project to query, so it:
   - Generates plausible-sounding text about "retrieving data"
   - Hallucinates errors ("tool error", "404 Not Found")
   - Never actually invokes the tools

### Debug Evidence

```
📋 PLAN INFO: plan_title='Sprint 4 Performance Analysis'  # ❌ No project_id!
📥 AGENT INPUT: messages_count=1
📥 Content: # Research Topic\n\nSprint 4 Performance Analysis...  # ❌ No project_id!
```

## Solution Options

### Option A: Extract and Pass project_id (RECOMMENDED)
1. Extract `project_id` from user message in the planner
2. Add `project_id` field to the State
3. Include it in the step description or agent input
4. Modify PM Agent prompt to use the project_id

### Option B: Improve Prompt to Force Tool Use
1. Make the PM Agent prompt more aggressive about tool calling
2. Add examples of tool calls in the prompt
3. Use a stronger LLM model (gpt-4 instead of gpt-4o-mini)

### Option C: Use Function Calling Mode
1. Configure the LLM to use strict function calling mode
2. Force the agent to ONLY respond with tool calls
3. Prevent text-only responses

## Recommended Next Steps

1. **Immediate**: Test with project_id in the step description manually
2. **Short-term**: Implement Option A (extract project_id)
3. **Long-term**: Consider Option C for reliability

## Files Modified

- `src/graph/nodes.py`: Changed HumanMessage → AIMessage (line 982)
- `src/server/app.py`: Added debug logging for message streaming
- `src/agents/agents.py`: Added debug logging for agent creation
- `src/prompts/template.py`: Added debug logging for prompt application

## Test Commands

```bash
# Test PM Agent with Sprint 4 query
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Analyze Sprint 4\n\nproject_id: d7e300c6-d6c0-4c08-bc8d-e41967458d86:478"}],
    "max_plan_iterations": 1,
    "max_step_num": 1,
    "auto_accepted_plan": true
  }' \
  --no-buffer
```

## Conclusion

The PM Agent infrastructure is working correctly:
- ✅ Tools are loaded
- ✅ Agent is created
- ✅ Messages are streamed

The issue is **LLM behavior**: The model generates text ABOUT using tools instead of actually calling them, primarily because the critical `project_id` context is missing from the agent's input.

