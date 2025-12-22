# MCP Meeting Server - AI Context

## When to Use This Module
- Exposing meeting tools to AI agents (Claude, GPT)
- Adding new MCP tools for meetings
- Changing server transport or configuration

## Quick Reference

### Start Server
```bash
python scripts/run_meeting_mcp_server.py --port 8082
```

### Tool Call Format
```json
{
  "name": "analyze_transcript",
  "arguments": {
    "transcript": "Alice: Let's discuss the API...",
    "title": "Sprint Planning",
    "participants": ["Alice", "Bob"]
  }
}
```

### Add a New Tool
Edit `tools/__init__.py`:
```python
@server.call_tool()
async def call_tool(name: str, arguments: Dict) -> List[Dict]:
    if name == "my_new_tool":
        return await _handle_my_new_tool(mcp_server, arguments)
```

## Tool Response Format
```python
return [{
    "type": "text",
    "text": "Result message here"
}]
```

## Error Handling
```python
try:
    # Tool logic
    return [{"type": "text", "text": "Success"}]
except Exception as e:
    return [{"type": "text", "text": f"Error: {str(e)}"}]
```

## Don't Forget
- Tools are defined in `tools/__init__.py`
- Server uses `meeting_agent.handlers.MeetingHandler` internally
- In-memory storage by default (replace with DB for production)
- SSE transport for Claude Desktop, HTTP for REST clients

## Related Modules
- `meeting_agent/` - Core processing
- `shared/mcp_tools/` - Base tool classes
