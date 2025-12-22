# MCP Server (PM) - AI Context

## When to Use This Module
- Adding/modifying PM MCP tools
- Changing MCP server configuration
- Debugging tool execution
- Adding new PM integrations

## Quick Reference

### Tool Locations
| Category | Path |
|----------|------|
| Sprint Tools | `tools/sprints/` |
| Task Tools | `tools/tasks/` |
| Epic Tools | `tools/epics/` |
| Analytics Tools | `tools/analytics/` |
| Provider Tools | `tools/providers/` |

### Add a New Tool
1. Create tool file in appropriate `tools/` subfolder
2. Use `@mcp_server.tool()` decorator
3. Register in `tools/__init__.py`

```python
@mcp_server.tool()
async def my_pm_tool(
    project_id: str,
    param: str,
) -> str:
    """Tool description for AI"""
    context = get_tool_context()
    # Implementation
    return json.dumps(result)
```

### Tool Context
```python
from mcp_server.core.tool_context import get_tool_context

context = get_tool_context()
context.user_id       # Current user
context.provider_id   # PM provider
context.get_handler() # PM handler instance
```

## Important Patterns
- All tools return JSON strings
- Use `get_tool_context()` for user/provider access
- Tools are registered via decorators
- Error handling returns error string, not exception

## Don't Forget
- Tool docs become AI prompts - be precise
- Parameter descriptions are important
- Check user permissions via context
- Database is in `db/` - user settings, API keys

## Related Modules
- `backend/` - PM agents and graphs
- `shared/mcp_tools/` - Base tool classes
- `pm_providers/` - PM system integrations
