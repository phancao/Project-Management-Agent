# Tool Execution Errors

Common issues with PM tool execution.

## Missing Method/Attribute

### Error Pattern
```
"'PMServiceHandler' object has no attribute 'method_name'"
```

### Cause
Tool calls a method that doesn't exist on handler.

### Fix
1. Check `pm_service_client.py` for available methods
2. Add missing method as alias or implement

### Example
```python
# pm_tools.py calls:
handler.single_provider.list_users()

# But PMServiceHandler only has:
list_project_users()

# Fix: Add alias method
async def list_users(self, project_id=None):
    return await self.list_project_users(project_id)
```

---

## Dict vs Object Access

### Error Pattern
```
"'dict' object has no attribute 'id'"
```

### Cause
Code expects object attributes but receives dict.

### Fix
```python
# Before (wrong):
users = [{"id": u.id, "name": u.name} for u in results]

# After (correct):
users = [{"id": u.get("id"), "name": u.get("name")} for u in results]
```

---

## Project ID Format Issues

### Error Pattern
```
"Invalid project_id format"
```

### Cause
Project ID includes provider prefix (`provider_id:project_id`).

### Fix
```python
# Extract actual project ID
if ":" in project_id:
    actual_id = project_id.split(":", 1)[1]
```

---

## Tool Not Found

### Error Pattern
```
"Tool 'tool_name' not available"
```

### Check
- Is tool in `get_pm_tools()` list?
- Is tool decorated with `@tool`?
