# ReAct Agent Routing Fix Plan

## Current Status (Latest Fix)

**✅ SOLUTION 6 IMPLEMENTED** - Fixed routing logic in `pm_chat_stream` endpoint

**Root Cause**: `needs_research = True` was hardcoded, forcing all queries to DeerFlow and bypassing coordinator/ReAct entirely.

**Fix Applied**: 
- Removed hardcoded routing
- Added PM intent detection
- PM queries → coordinator → ReAct
- Non-PM queries → DeerFlow

**Status**: Backend restarted, awaiting test results

---

## Problem Summary

**Issue**: ReAct agent is not being used for simple PM queries - system goes directly to Planner, bypassing coordinator and ReAct.

**Root Cause Found** (from latest investigation):
1. ❌ **CRITICAL**: `needs_research = True` was hardcoded in `src/server/app.py` line 3297
2. ❌ This forced ALL queries to DeerFlow (research flow), bypassing coordinator entirely
3. ❌ Coordinator was never called, so ReAct was never invoked
4. ❌ System went directly to Planner for all queries

**Log Evidence**:
```
[REACT-AGENT] ⚠️ No intermediate steps - agent may not have called any tools
[REACT-AGENT] 🔍 Output looks like failure/greeting: 'Hello! How can I help you with your project management tasks today?...'
[REACT-AGENT] ⬆️ Escalating to planner: pm_request_failed: PM request but output looks like failure/greeting
```

## Attempted Solutions

### Solution 1: Add PM Intent Check in Clarification Branch ✅
**Status**: Implemented but doesn't solve the root cause
**File**: `src/graph/nodes.py` (lines 1112-1151)
**What it does**: Routes PM queries to ReAct even when clarification is enabled
**Result**: Routing works, but ReAct still escalates

### Solution 2: Fix ReAct Prompt ✅
**Status**: Implemented
**File**: `src/graph/nodes.py` (lines 4724-4772)
**Problem**: ReAct prompt checked for greetings FIRST, so "ok. tell me description of this project" was treated as greeting
**Root Cause**: ReAct shouldn't check for greetings at all - coordinator already handles greetings and routes them to END. If a message reaches ReAct, it's already a PM query.
**Fix Attempt 1**: Removed all greeting handling from ReAct prompt. Simplified to focus only on executing PM queries.
**Result**: ❌ FAILED - ReAct still responded with greetings ("Hello! How can I help you...")

**Fix Attempt 2**: Made prompt much more forceful and explicit:
- Added "CRITICAL: DO NOT respond with greetings - EXECUTE THE QUERY IMMEDIATELY"
- Added "MANDATORY WORKFLOW" section
- Added "FORBIDDEN RESPONSES" section with explicit examples
- Added warning: "If you respond with greetings instead of calling tools, the system will escalate"
- Made it clear: Call `get_current_project` FIRST, no text responses before tools
**Result**: ✅ PARTIAL SUCCESS - ReAct now calls tools! But ❌ NEW ISSUE: ReAct gets stuck in loop calling `get_current_project` repeatedly, hitting recursion limit of 8

**New Issue Found** (from latest logs):
- ReAct IS calling `get_current_project` (prompt fix worked!)
- But it calls it multiple times in a loop (8+ times)
- Hits recursion limit: "Recursion limit of 8 reached without hitting a stop condition"
- Same thought extracted repeatedly: "I need to use get_current_project to answer the user's question"
- Tool results are being processed, but agent keeps calling the tool again

**Root Cause Hypothesis for Loop**:
- Prompt was TOO forceful and prescriptive - confused the agent
- Agent didn't understand what to do AFTER getting the result
- Tool result format (JSON string) might need better explanation
- Need simpler, more natural prompt that guides without forcing

**Fix Attempt 3**: Reverted to simpler, more natural prompt:
- Removed all "CRITICAL", "MANDATORY", "FORBIDDEN" language
- Simplified to natural workflow description
- Let agent figure out the flow naturally instead of forcing it
- Still emphasizes calling `get_current_project` first, but more gently
**Result**: ❌ FAILED - ReAct still loops calling `get_current_project` repeatedly (8+ times), hitting recursion limit

**Root Cause Analysis**:
- ReAct IS calling tools now (prompt fix worked!)
- But agent gets stuck in loop calling `get_current_project` repeatedly
- Agent doesn't understand what to do AFTER getting the result
- Tool returns JSON string - agent might not know how to parse/use it
- Forcing "call get_current_project first" might be causing the loop

**Fix Attempt 4**: Reverted to minimal prompt (closest to original):
- Removed all workflow instructions
- Removed forced "call get_current_project first"
- Simple: "Use tools to answer the question"
- Only mentions `get_current_project` as an option if user says "this project"
- Let agent decide naturally what tools to call
**Result**: ❌ FAILED - ReAct still responds with greeting ("Awaiting your PM query....") instead of calling tools

**Fix Attempt 5**: Made prompt even more forceful:
- Added "CRITICAL RULES" section with explicit "DO NOT" statements
- Added example workflow
- Emphasized "CALL TOOLS IMMEDIATELY"
- Fixed failure detection to check first 300 chars (not just < 200 total)
- Changed tool result format from JSON to plain text with clear instructions
**Result**: ❌ FAILED - ReAct STILL responds with greeting ("Awaiting your PM query....", "I'm ready to help...") instead of calling tools

**Current Status (from latest logs)**:
- ✅ Tools are available: `get_current_project` is in the tool list
- ✅ Coordinator routes correctly to ReAct
- ❌ ReAct responds with greeting text instead of calling tools
- ❌ Messages are being duplicated (same HumanMessage/AIMessage repeated)
- ❌ Planner uses wrong tool name: `get_current_project_details()` instead of `get_current_project`

**Root Cause Hypothesis**:
The prompt changes aren't working because:
1. LangGraph's `create_react_agent` might not be applying our prompt correctly
2. The agent might be using a different prompt template
3. The conversation history duplication might be confusing the agent
4. The agent might need explicit tool calling examples in the prompt

**Key Insight**: The real root cause was NOT the prompt - it was the routing logic in `src/server/app.py` that was hardcoded to always route to DeerFlow, completely bypassing the coordinator and ReAct agent.

## Solution 6: Fix Routing Logic in pm_chat_stream ✅ (LATEST)

**Status**: ✅ IMPLEMENTED
**File**: `src/server/app.py` (lines 3293-3465)
**Root Cause**: `needs_research = True` was hardcoded, forcing all queries to DeerFlow
**Fix**:
1. Removed hardcoded `needs_research = True`
2. Added PM intent detection BEFORE routing decision
3. Routing logic:
   - **PM queries** (`has_pm_intent = True`): Route to PM graph (coordinator → ReAct) via `_astream_workflow_generator`
   - **Non-PM queries** (`has_pm_intent = False`): Route to DeerFlow (research flow) via `_astream_workflow_generator`
4. Both use the same global `graph` instance, but coordinator routes PM queries to ReAct

**Changes Made**:
- Removed hardcoded `needs_research = True` (line 3297)
- Moved PM intent detection before routing decision
- Set `needs_research = not has_pm_intent` (PM queries don't need research)
- Added else branch for PM queries to route to PM graph
- PM queries now properly go through coordinator → ReAct flow

**Expected Result**:
- PM queries like "what is the description of this project" should:
  1. ✅ Detect PM intent
  2. ✅ Route to coordinator → ReAct
  3. ✅ ReAct calls `get_current_project` (returns JSON with `project_id`)
  4. ✅ ReAct calls `get_project(project_id="...")` to get description
  5. ✅ ReAct thoughts are displayed

**Status**: Backend restarted, awaiting test results

## Next Steps

1. **Check ReAct prompt** (`react_prompt_func` in `src/graph/nodes.py`)
   - Ensure it explicitly instructs to call `get_current_project` for PM queries
   - Remove or tighten greeting handling for PM queries

2. **Test the fix** using browser MCP

3. **If still doesn't work**: Revert Solution 1 and try a different approach

## Files Modified

- `src/graph/nodes.py`: 
  - Added PM intent check in clarification branch (lines 1112-1151)
  - Updated ReAct prompt to handle JSON output from `get_current_project` (lines 4726-4772)
- `src/tools/pm_tools.py`: 
  - Modified `get_current_project` to return structured JSON instead of plain text
- `src/server/app.py`: 
  - **CRITICAL FIX**: Removed hardcoded `needs_research = True` (line 3297)
  - Added proper PM intent detection and routing logic (lines 3293-3465)
  - PM queries now route to coordinator → ReAct, non-PM queries route to DeerFlow
- `web/src/app/pm/chat/components/step-box.tsx`: Added friendly names for `backend_api_call`, `get_current_project`, `optimize_context`

