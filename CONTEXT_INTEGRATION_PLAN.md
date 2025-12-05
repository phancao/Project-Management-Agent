# Context Management Integration Plan

## Current Architecture Analysis

### 1. **User Model Selection** ✅ Already Handled!

**Flow:**
```
UI Combobox (model selection)
    ↓
web/src/core/store/settings-store.ts (modelProvider, modelName)
    ↓
web/src/core/api/chat.ts (passes in request)
    ↓
backend/server/app.py (line 1164-1169)
    ↓
src/llms/llm.py: set_model_selection(provider, model)
    ↓
Context variables: _model_provider_ctx, _model_name_ctx
    ↓
get_llm_by_type() uses these context variables
```

**Good news:** Our `_create_summary_message()` already uses `get_llm_by_type("basic")` which respects the user's selection! ✅

---

### 2. **Existing Context Storage Systems**

We have **THREE** separate context storage systems:

#### A. Frontend Context (UI State)
**Location:** `web/src/core/store/store.ts`
```typescript
buildConversationHistory(messages, messageIds, 20)
// Keeps last 20 messages in browser memory
```

#### B. Backend Session Context (In-Memory)
**Location:** `src/conversation/flow_manager.py`
```python
class ConversationFlowManager:
    self.contexts: Dict[str, ConversationContext] = {}
    # Stores: conversation_history, intent, gathered_data
```

#### C. LangGraph State (Per-Request)
**Location:** `src/graph/types.py`
```python
class State(MessagesState):
    messages: list[BaseMessage]  # Full conversation in this request
    # Gets compressed by ContextManager during agent execution
```

---

## The Problem: Disconnected Systems

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Frontend (UI)  │────▶│  FlowManager     │────▶│  LangGraph      │
│  Last 20 msgs   │     │  Session context │     │  Per-request    │
│  (browser)      │     │  (in-memory)     │     │  (compressed)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
       ↓                         ↓                        ↓
   Not shared            Not shared with           Our new compression
   with backend          LangGraph                 happens here!
```

**Issues:**
1. Frontend sends only last 20 messages → Backend doesn't see full history
2. FlowManager stores context but LangGraph doesn't use it
3. Our new ContextManager compresses LangGraph state but doesn't integrate with FlowManager

---

## Recommended Integration Strategy

### Option 1: **Merge into FlowManager** (Recommended) ✅

**Approach:**
- Store compressed summaries in `ConversationContext`
- Reuse summaries across requests
- Integrate with existing session management

**Implementation:**
```python
class ConversationContext:
    session_id: str
    conversation_history: List[Dict[str, str]]
    
    # NEW: Add compression state
    compressed_summaries: List[Dict[str, Any]] = []  # Cached summaries
    last_summary_at: int = 0  # Message index when last summarized
    compression_strategy: str = "hierarchical"
```

**Benefits:**
- ✅ Reuses existing session management
- ✅ Summaries persist across requests
- ✅ No duplicate storage
- ✅ Integrates with existing code

---

### Option 2: **Shared Context Service** (Advanced)

**Approach:**
- Create unified context service
- All systems read/write from same place
- Centralized compression logic

**Too complex for now** - Option 1 is better.

---

## Implementation Plan

### Step 1: Extend ConversationContext

**File:** `src/conversation/flow_manager.py`

```python
@dataclass
class ConversationContext:
    session_id: str
    current_state: FlowState
    intent: IntentType
    gathered_data: Dict[str, Any]
    required_fields: List[str]
    conversation_history: List[Dict[str, str]]
    created_at: datetime
    updated_at: datetime
    
    # NEW: Compression state
    compressed_summaries: List[str] = field(default_factory=list)
    last_summary_at: int = 0  # Index when last summarized
    summary_cache_key: Optional[str] = None
```

---

### Step 2: Add Compression Methods to FlowManager

```python
class ConversationFlowManager:
    def get_compressed_context(
        self, 
        session_id: str,
        agent_type: str = "default"
    ) -> List[BaseMessage]:
        """
        Get compressed conversation context for LangGraph.
        
        Uses cached summaries from ConversationContext.
        """
        context = self.contexts.get(session_id)
        if not context:
            return []
        
        # Convert conversation_history to BaseMessages
        messages = self._history_to_messages(context.conversation_history)
        
        # Check if we need to create new summary
        if len(messages) - context.last_summary_at > 30:
            # Time to create new summary
            old_messages = messages[context.last_summary_at:-10]
            
            from src.utils.agent_context_config import get_context_manager_for_agent
            cm = get_context_manager_for_agent(agent_type)
            
            summary = cm._create_summary_message(old_messages)
            context.compressed_summaries.append(summary.content)
            context.last_summary_at = len(messages) - 10
            
            logger.info(f"[FLOW-MANAGER] Created summary for {len(old_messages)} messages")
        
        # Build compressed context: summaries + recent messages
        compressed = []
        
        # Add all summaries
        for summary_text in context.compressed_summaries:
            compressed.append(SystemMessage(content=summary_text, name="context_summary"))
        
        # Add recent messages (last 10)
        compressed.extend(messages[-10:])
        
        return compressed
```

---

### Step 3: Use FlowManager Context in LangGraph

**File:** `backend/server/app.py`

```python
# When starting DeerFlow workflow
async for event in _stream_graph_events(...):
    # Before: LangGraph only sees current request messages
    # After: LangGraph gets compressed context from FlowManager
    
    # Get compressed context from FlowManager
    compressed_context = fm.get_compressed_context(session_id, agent_type="planner")
    
    # Pass to LangGraph
    initial_state = {
        "messages": compressed_context + current_request_messages,
        ...
    }
```

---

## Benefits of Integration

| Before | After Integration |
|--------|-------------------|
| 3 separate context systems | 1 unified system |
| Summaries lost between requests | Summaries cached in session |
| Frontend sends only 20 messages | Backend has full compressed history |
| Re-summarize every request | Reuse cached summaries |
| No cross-request optimization | Smart incremental compression |

---

## Quick Fix for Now (Minimal Change)

Since full integration is complex, let's do a **quick fix** first:

**Just ensure user's model is used for summarization** (already done! ✅)

The code already works:
```python
# src/utils/context_manager.py line 440
llm = get_llm_by_type("basic")  # ← Uses user's selected model via context vars!
```

When user selects a model in UI:
1. UI sends `model_provider` and `model_name` in request
2. Backend calls `set_model_selection(provider, model)` (line 1166)
3. Context variables are set
4. `get_llm_by_type()` reads these and uses user's model
5. Summarization uses user's selected model ✅

---

## Full Integration (Phase 2 - Optional)

If you want full integration with FlowManager:

1. Add compression state to `ConversationContext`
2. Store summaries in session (persist across requests)
3. Pass compressed context to LangGraph
4. Incremental summarization (only new messages)

**Estimated time:** 4-6 hours
**Benefits:** 
- Summaries reused across requests (faster)
- Better context continuity
- Less redundant summarization

---

## Current Status

✅ **User's model selection is ALREADY respected!**
- `get_llm_by_type("basic")` uses context variables
- User's selected model is used for summarization
- No changes needed!

❓ **Do you want full FlowManager integration?**
- Would take 4-6 hours
- Adds summary caching across requests
- Better for multi-turn conversations

For now, the implementation already respects user's model choice! 🎯


