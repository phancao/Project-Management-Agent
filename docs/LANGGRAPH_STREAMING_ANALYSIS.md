# LangGraph Streaming Capabilities Analysis

## Overview
This document analyzes LangGraph's built-in streaming capabilities and identifies opportunities to improve our research steps/content streaming implementation.

## Current Implementation
We're currently using:
- `stream_mode=["messages", "updates"]` in `graph.astream()`
- Manual parsing of state updates from the `updates` stream
- Custom event generation for `plan_update` and `step_update`

## LangGraph Stream Modes

### Available Stream Modes
1. **`"messages"`** - Streams LangChain messages (AIMessage, HumanMessage, ToolMessage, etc.)
   - What we're already using ✓
   - Provides message chunks for streaming responses

2. **`"updates"`** - Streams state updates by node
   - What we're already using ✓
   - Returns dicts keyed by node name with their state changes
   - Format: `{node_name: {state_field: new_value}}`

3. **`"values"`** - Streams full state snapshots
   - Not currently used
   - Returns complete state after each update
   - Could be useful for debugging but verbose for production

4. **`"debug"`** - Structured debug events
   - Not currently used
   - Provides structured events:
     - `task` events (when tasks start)
     - `task_result` events (when tasks complete)
     - `checkpoint` events (state checkpoints)
   - Each event has: `type`, `timestamp`, `step`, `payload`
   - **Potential benefit**: Could use this to track node execution more precisely

5. **`"events"`** - Not supported in local Pregel
   - Only available in remote/LangGraph Cloud
   - Not applicable to our use case

## Key Findings

### 1. Current Approach is Correct
Our implementation correctly uses `stream_mode=["messages", "updates"]`:
- ✅ `messages` gives us agent responses and tool calls
- ✅ `updates` gives us state changes (plan updates, observations)

### 2. Opportunity: Use `"debug"` Mode for Better Node Tracking
The `debug` stream mode provides structured events that could help us:
- Track when nodes start/complete execution
- Get precise timestamps for each step
- See task IDs and names

**Example debug event structure:**
```python
{
    "type": "task_result",
    "timestamp": "2025-11-05T09:00:00Z",
    "step": 3,
    "payload": {
        "id": "task_123",
        "name": "planner",  # node name
        "error": None,
        "result": [...],
        "interrupts": []
    }
}
```

### 3. State Updates Structure (What We're Using)
When using `stream_mode=["messages", "updates"]`, updates come as:
```python
{
    "planner": {
        "current_plan": Plan(...),
        "messages": [...]
    },
    "research_team": {
        "observations": ["finding 1", "finding 2"]
    }
}
```

This matches our current implementation where we iterate through node updates.

## Recommendations

### Option 1: Add `"debug"` Mode (Recommended)
Add `"debug"` to stream modes to get structured execution events:

**Pros:**
- Precise node execution tracking
- Timestamps for each step
- Task IDs for correlation
- Better observability

**Cons:**
- Additional stream events to process
- More verbose output

**Implementation:**
```python
async for agent, stream_type, event_data in graph_instance.astream(
    workflow_input,
    config=workflow_config,
    stream_mode=["messages", "updates", "debug"],  # Add debug
    subgraphs=True,
):
    if stream_type == "debug":
        # Process structured debug events
        if event_data.get("type") == "task_result":
            node_name = event_data["payload"]["name"]
            # Track node completion
```

### Option 2: Use `"values"` Mode for Complete State (Alternative)
Stream full state snapshots to have complete context:

**Pros:**
- Complete state available at each step
- No need to reconstruct state from updates

**Cons:**
- Very verbose
- Duplicate data (we already get updates)
- Not recommended for production streaming

### Option 3: Keep Current Approach (Simplest)
Continue with current implementation, but consider:
- Adding debug mode for observability/logging
- Not streaming debug events to client (too verbose)
- Using debug events only server-side for monitoring

## Conclusion

**Best Approach: Hybrid**
1. Keep `stream_mode=["messages", "updates"]` for client streaming ✓
2. Optionally add `"debug"` mode for server-side logging/monitoring
3. Continue extracting plan/step updates from `"updates"` stream as we do now

Our current implementation is correct and follows LangGraph best practices. The `"debug"` mode could add value for observability but isn't necessary for the core functionality.

## Current Code Location
- Stream processing: `src/server/app.py::_stream_graph_events()`
- Event generation: `src/server/app.py::_make_event()`
- State update extraction: Lines 545-625 in `_stream_graph_events()`
