# Routing Issues

Common issues with PM query routing.

## Query Not Reaching PM Agent

### Symptoms
- Generic response (e.g., "DeerFlow" greeting)
- No PM data returned
- No `[PM-AGENT]` logs

### Check
```
Look for: [COORDINATOR] PM intent detection
Expected: has_pm_intent=True
```

### Causes & Fixes

| Cause | Fix |
|-------|-----|
| Non-English query | LLM fallback should catch (see [02_intent_detection.md](../architecture/02_intent_detection.md)) |
| Missing keyword | Add to `pm_keywords` list |
| LLM fallback skipped | Check message length > 5 chars |

---

## Query Going to Planner Instead of ReAct

### Symptoms
- Multi-step plan for simple query
- Slow response for quick questions

### Check
```
Look for: [COORDINATOR] User needs escalation
```

### Fix
- Single queries should NOT trigger `detect_user_needs_more_detail()`
- Only escalate on explicit "more detail" requests

---

## Wrong Project Context

### Symptoms
- "No project selected" error
- Empty results for PM queries

### Check
```
Look for: [PM-AGENT] 📝 Project ID: 
Expected: Project ID should be populated
```

### Fix
- Ensure `set_current_project_id()` called before PM agent
- Check project selection in UI header
