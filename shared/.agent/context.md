# Shared Library - AI Context

## When to Use This Module
- Building a new agent that needs handlers, analytics, or MCP tools
- Creating reusable patterns that both PM Agent and Meeting Agent can use
- Adding common data models (charts, work items)

## Key Patterns

### Handler Pattern
All agents use `BaseHandler` for consistent operation execution:
```python
class MyHandler(BaseHandler[OutputType]):
    async def execute(self, context: HandlerContext, **kwargs) -> HandlerResult[OutputType]:
        # Validate
        error = await self.validate(context, **kwargs)
        if error:
            return HandlerResult.failure(error)
        
        # Execute
        result = await self._do_work(context, **kwargs)
        return HandlerResult.success(result)
```

### MCP Tool Pattern
Use decorators for metadata:
```python
@mcp_tool(
    name="my_tool",
    description="Does something",
    category=ToolCategory.READ,
)
@require_project
async def my_tool(context, project_id: str) -> ToolResult:
    return ToolResult.ok(data)
```

## Don't Forget
- HandlerResult has `.is_success`, `.is_failed`, `.data`, `.message`
- ToolResult has `.ok()`, `.fail()`, `.to_mcp_response()`
- ChartType enum includes meeting types: MEETING_DURATION, PARTICIPANT_ENGAGEMENT

## Related Modules
- `meeting_agent/` - Uses handlers/analytics
- `backend/` - Uses handlers/analytics
- `mcp_server/` - Uses mcp_tools
