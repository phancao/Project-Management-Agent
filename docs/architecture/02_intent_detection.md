# Intent Detection (Hybrid)

**Log Prefix:** `[COORDINATOR] PM intent`, `[COORDINATOR] 🤖 LLM`  
**File:** `backend/graph/nodes.py` → `classify_pm_intent_with_llm()`

## How It Works

```
User Message
     ↓
Step 1: Keyword Check (0ms)
     ↓ no match
Step 2: LLM Check (~200-500ms)
     ↓
Route Decision
```

## Keywords (English)

```python
pm_keywords = [
    "sprint", "task", "project", "user", "epic", "backlog",
    "burndown", "velocity", "assign", "assignee", "team member",
    "work package", "milestone", "status", "priority", "list",
    "show", "get", "analyze", "report", "health", "dashboard"
]
```

## LLM Fallback (Multilingual)

```python
def classify_pm_intent_with_llm(user_message: str) -> bool:
    prompt = """Classify this message. Is it about Project Management?
    (tasks, sprints, projects, team members, epics...)
    
    Message: "{user_message}"
    Reply: PM or NOT_PM"""
    
    return "PM" in llm.invoke(prompt).content.upper()
```

## Debug Logs

| Log | Meaning |
|-----|---------|
| `Keywords missed, trying LLM fallback` | Keyword check failed, LLM checking |
| `🤖 LLM intent classification: '...' → True` | LLM detected PM |
| `✅ LLM detected PM intent (multilingual)` | Routing to react_agent |

## Test Cases

| Query | Keyword | LLM | Route |
|-------|---------|-----|-------|
| "list sprints" | ✅ | skip | react_agent |
| "dự án này có ai?" | ❌ | ✅ | react_agent |
| "hello" | ❌ | skip | END |
