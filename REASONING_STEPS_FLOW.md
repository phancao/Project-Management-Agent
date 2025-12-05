# Reasoning Steps (Thoughts) Flow

## Overview
This document traces where reasoning steps (thoughts) are generated, extracted, stored, and displayed in the ReAct agent flow.

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. LLM GENERATION (LangGraph ReAct Agent)                      │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────┐
    │ LangGraph Agent Graph                   │
    │ - Uses structured tool calling          │
    │ - LLM generates AIMessage with:         │
    │   • tool_calls: [{name, args}]          │
    │   • content: "" (empty for tool calls)  │
    │   • additional_kwargs.reasoning_content │
    │     (if model supports it, e.g., o1)    │
    └─────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. EXTRACTION (react_agent_node - lines 4525-4567)             │
└─────────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
┌──────────────────┐              ┌──────────────────┐
│ During astream   │              │ After completion │
│ (incremental)    │              │ (final)          │
└──────────────────┘              └──────────────────┘
        │                                   │
        │ Lines 4525-4567                   │ Lines 4654-4720
        │                                   │
        │ Extract from:                     │ Extract from:
        │ • additional_kwargs.reasoning_    │ • additional_kwargs.reasoning_
        │   content                         │   content
        │ • content (if "Thought:" pattern) │ • content (if "Thought:" pattern)
        │ • Generate fallback based on      │ • Generate fallback based on
        │   tool name                       │   tool name
        │                                   │
        │ Store in:                         │ Store in:
        │ • incremental_thoughts[]          │ • thoughts[]
        │ • msg.additional_kwargs           │
        │   ["react_thoughts"]              │
        │                                   │
        └─────────────────┬─────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. STORAGE (react_agent_node - lines 5221-5232)                │
└─────────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
┌──────────────────┐              ┌──────────────────┐
│ Final Message    │              │ State Update     │
│ additional_kwargs│              │                  │
└──────────────────┘              └──────────────────┘
        │                                   │
        │ Line 5222:                        │ Line 5232:
        │ final_message.additional_kwargs   │ Command(update={
        │   ["react_thoughts"] = thoughts   │   "react_thoughts": thoughts
        │                                   │ })
        │                                   │
        └─────────────────┬─────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. STREAMING (backend/server/app.py)                           │
└─────────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
┌──────────────────┐              ┌──────────────────┐
│ From Message     │              │ From State       │
│ additional_kwargs│              │ node_update      │
└──────────────────┘              └──────────────────┘
        │                                   │
        │ Line 1113-1119:                   │ Line 1113-1119:
        │ Check msg.additional_kwargs       │ Check node_update
        │   ["react_thoughts"]              │   ["react_thoughts"]
        │                                   │
        │ Line 480-484:                     │
        │ _create_event_stream_message()    │
        │   adds react_thoughts to event    │
        │                                   │
        └─────────────────┬─────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. FRONTEND RECEIVING (web/src/core/messages/merge-message.ts) │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │ Line 130-132:
                          │ if (event.data.react_thoughts) {
                          │   message.reactThoughts = 
                          │     event.data.react_thoughts
                          │ }
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. FRONTEND DISPLAY (web/src/app/pm/chat/components/)          │
└─────────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
┌──────────────────┐              ┌──────────────────┐
│ Collection       │              │ Rendering        │
│ (analysis-block) │              │ (analysis-block) │
└──────────────────┘              └──────────────────┘
        │                                   │
        │ Lines 116-142:                    │ Lines 303-316:
        │ Collect thoughts from messages    │ Render ThoughtBox
        │ with agent === "react_agent"      │ components
        │                                   │
        │ Filter by:                        │ Display:
        │ • message.reactThoughts           │ • Thought icon (Brain)
        │ • message.agent === "react_agent" │ • Thought text
        │                                   │ • Step number
        │                                   │
        └─────────────────┬─────────────────┘
                          │
                          ▼
                    ┌──────────┐
                    │   UI     │
                    │ Thought  │
                    │   Box    │
                    └──────────┘
```

## Key Locations

### 1. **Extraction Points**

#### A. During Streaming (Incremental)
- **File**: `src/graph/nodes.py`
- **Lines**: 4525-4567
- **Location**: Inside `astream` loop
- **Purpose**: Extract thoughts as they're generated
- **Methods**:
  1. Check `additional_kwargs.reasoning_content` (if model supports it)
  2. Parse `content` for "Thought:" pattern (text-based ReAct)
  3. Generate fallback based on tool name

#### B. After Completion (Final)
- **File**: `src/graph/nodes.py`
- **Lines**: 4654-4720
- **Location**: After `astream` completes
- **Purpose**: Extract thoughts from all messages
- **Methods**: Same as above, but processes all messages at once

### 2. **Storage Points**

#### A. Message Level
- **File**: `src/graph/nodes.py`
- **Lines**: 4565-4567, 5222
- **Location**: `msg.additional_kwargs["react_thoughts"]`
- **Purpose**: Attach thoughts to individual messages for streaming

#### B. State Level
- **File**: `src/graph/nodes.py`
- **Line**: 5232
- **Location**: `Command(update={"react_thoughts": thoughts})`
- **Purpose**: Store thoughts in state for backend access

### 3. **Streaming Points**

#### A. Backend Detection
- **File**: `backend/server/app.py`
- **Lines**: 1113-1119
- **Location**: Inside `_stream_graph_events`
- **Purpose**: Check for thoughts in both message and state

#### B. Event Creation
- **File**: `backend/server/app.py`
- **Lines**: 480-484
- **Location**: `_create_event_stream_message`
- **Purpose**: Include `react_thoughts` in stream event

### 4. **Frontend Points**

#### A. Message Merging
- **File**: `web/src/core/messages/merge-message.ts`
- **Lines**: 130-132
- **Location**: `mergeTextMessage` function
- **Purpose**: Store thoughts in message object

#### B. Collection
- **File**: `web/src/app/pm/chat/components/analysis-block.tsx`
- **Lines**: 116-142
- **Location**: `useMemo` hook
- **Purpose**: Collect thoughts from all messages

#### C. Display
- **File**: `web/src/app/pm/chat/components/analysis-block.tsx`
- **Lines**: 303-316
- **Location**: Render loop
- **Purpose**: Render `ThoughtBox` components

## Current Issues

### Problem: Thoughts Not Showing

**Root Cause**: With structured tool calling, the LLM doesn't generate "Thought:" text in the content. The content is empty when only tool calls are present.

**Why Method 1 Fails**: 
- `additional_kwargs.reasoning_content` only exists for models that support reasoning tokens (e.g., o1-preview, o3-mini)
- Most models (gpt-3.5-turbo, gpt-4) don't support this

**Why Method 2 Fails**:
- Content is empty for structured tool calls
- No "Thought:" pattern to extract

**Why Method 3 Works**:
- Generates fallback thoughts based on tool name
- Always produces something: "I'll use list_sprints to get the information I need."

## Solutions

### Option 1: Use Reasoning Models (Recommended)
- Switch to o1-preview or o3-mini
- These models explicitly support `reasoning_content`

### Option 2: Modify Prompt (Current)
- Add instruction: "Before calling a tool, explain your reasoning"
- Force LLM to include reasoning in content

### Option 3: Use Fallback Thoughts (Current)
- Generate descriptive thoughts based on tool name and args
- Always shows something, even if not from LLM

### Option 4: Hybrid Approach (Best)
- Use fallback thoughts as default
- If `reasoning_content` exists, use that instead
- If content has "Thought:" pattern, extract that

## Debug Commands

```bash
# Check if thoughts are extracted
docker logs pm-backend-api --tail 500 | grep "💭"

# Check message structure
docker logs pm-backend-api --tail 500 | grep "Found tool-calling message"

# Check if thoughts are streamed
docker logs pm-backend-api --tail 500 | grep "react_thoughts"

# Check frontend console
# Look for: message.reactThoughts in browser console
```

## Data Structure

### Thought Object
```typescript
{
  thought: string;        // The reasoning text
  before_tool: boolean;   // Always true (thoughts come before tool calls)
  step_index: number;     // Index in the sequence (0, 1, 2, ...)
}
```

### Message Structure
```typescript
{
  id: string;
  agent: "react_agent";
  reactThoughts?: Array<{
    thought: string;
    before_tool: boolean;
    step_index: number;
  }>;
  // ... other fields
}
```

