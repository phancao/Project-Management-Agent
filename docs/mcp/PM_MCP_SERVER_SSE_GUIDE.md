# PM MCP Server - SSE Transport Guide

## 🌐 Overview

The SSE (Server-Sent Events) transport enables web-based agents to connect to the PM MCP Server over HTTP with real-time streaming capabilities.

## 🚀 Quick Start

### 1. Start the SSE Server

```bash
# Start on default port (8080)
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport sse

# Start on custom port
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport sse --port 8081 --host 0.0.0.0
```

### 2. Verify Server is Running

```bash
# Check server info
curl http://localhost:8080/

# Check health
curl http://localhost:8080/health

# List available tools
curl -X POST http://localhost:8080/tools/list
```

## 📡 API Endpoints

### Root Endpoint
```http
GET /
```

Returns server information:
```json
{
  "name": "pm-server",
  "version": "0.1.0",
  "transport": "sse",
  "status": "running",
  "tools_count": 51
}
```

### Health Check
```http
GET /health
```

Returns health status:
```json
{
  "status": "healthy",
  "providers": 3,
  "tools": 51
}
```

### List Tools
```http
POST /tools/list
```

Returns all available tools:
```json
{
  "tools": [
    {
      "name": "list_projects",
      "description": "List all accessible projects...",
      "parameters": {}
    },
    ...
  ],
  "count": 51
}
```

### Call Tool (Non-Streaming)
```http
POST /tools/call
Content-Type: application/json

{
  "tool": "list_projects",
  "arguments": {
    "provider_id": "openproject-1"
  },
  "request_id": "req-123"
}
```

Response:
```json
{
  "request_id": "req-123",
  "tool": "list_projects",
  "result": [
    {
      "type": "text",
      "text": "Found 5 projects:\n..."
    }
  ],
  "success": true
}
```

### Call Tool (Streaming)
```http
POST /tools/call/stream
Content-Type: application/json

{
  "tool": "list_my_tasks",
  "arguments": {},
  "request_id": "req-456"
}
```

Streams SSE events:
```
event: start
data: {"request_id":"req-456","tool":"list_my_tasks","status":"executing"}

event: result
data: {"request_id":"req-456","tool":"list_my_tasks","result":[...],"success":true}

event: complete
data: {"request_id":"req-456","status":"completed"}
```

### SSE Endpoint
```http
GET /sse
```

Establishes persistent SSE connection:
```
event: connected
data: {"server":"pm-server","version":"0.1.0","tools_count":51}

event: tools
data: {"tools":[...],"count":51}

event: heartbeat
data: {"timestamp":"1234567890.123"}
```

## 🔧 Using with Web Agents

### JavaScript/TypeScript Example

```typescript
// Connect to SSE endpoint
const eventSource = new EventSource('http://localhost:8080/sse');

eventSource.addEventListener('connected', (event) => {
  const data = JSON.parse(event.data);
  console.log('Connected to PM MCP Server:', data);
});

eventSource.addEventListener('tools', (event) => {
  const data = JSON.parse(event.data);
  console.log(`Available tools: ${data.count}`);
});

// Call a tool
async function callTool(toolName: string, args: any) {
  const response = await fetch('http://localhost:8080/tools/call', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tool: toolName,
      arguments: args,
      request_id: crypto.randomUUID()
    })
  });
  
  return await response.json();
}

// Example: List projects
const result = await callTool('list_projects', {});
console.log(result);
```

### Python Example

```python
import httpx
import json

# Base URL
BASE_URL = "http://localhost:8080"

# List available tools
async def list_tools():
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/tools/list")
        return response.json()

# Call a tool
async def call_tool(tool_name: str, arguments: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/tools/call",
            json={
                "tool": tool_name,
                "arguments": arguments,
                "request_id": "req-001"
            }
        )
        return response.json()

# Example usage
tools = await list_tools()
print(f"Available tools: {tools['count']}")

result = await call_tool("list_my_tasks", {})
print(result)
```

### LangChain MCP Client Example

```python
from langchain_mcp import MultiServerMCPClient

# Connect to PM MCP Server via SSE
mcp_client = MultiServerMCPClient({
    "pm-server": {
        "transport": "sse",
        "url": "http://localhost:8080"
    }
})

# Load tools
pm_tools = await mcp_client.get_tools()

# Use in agent
from langchain.agents import create_react_agent
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")
agent = create_react_agent(llm, pm_tools, prompt)

# Run agent
result = agent.invoke({"input": "List all my tasks"})
print(result)
```

## 🔐 Security Considerations

### CORS Configuration

By default, the SSE server allows all origins (`*`). For production:

```python
# In transports/sse.py, modify:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
```

### Authentication

Add authentication middleware:

```python
from fastapi import Header, HTTPException

@app.middleware("http")
async def authenticate(request: Request, call_next):
    token = request.headers.get("Authorization")
    if not token or not verify_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    response = await call_next(request)
    return response
```

### Rate Limiting

Use FastAPI rate limiting:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/tools/call")
@limiter.limit("10/minute")
async def call_tool(request: Request, mcp_request: MCPRequest):
    # ... tool call logic
```

## 📊 Monitoring

### Logging

All tool calls are logged:
```
INFO:pm_server.sse:Tool call: list_projects with args: {'provider_id': 'openproject-1'}
INFO:pm_server.sse:SSE connection established
```

### Metrics

Track tool usage:
```python
from prometheus_client import Counter, Histogram

tool_calls = Counter('pm_mcp_tool_calls', 'Tool calls', ['tool_name'])
tool_duration = Histogram('pm_mcp_tool_duration', 'Tool duration', ['tool_name'])

@app.post("/tools/call")
async def call_tool(request: MCPRequest):
    tool_calls.labels(tool_name=request.tool).inc()
    with tool_duration.labels(tool_name=request.tool).time():
        # ... tool execution
```

## 🐛 Troubleshooting

### Connection Refused

```bash
# Check if server is running
curl http://localhost:8080/health

# Check logs
tail -f logs/pm_mcp_server.log
```

### CORS Errors

Add your origin to allowed origins in `transports/sse.py`.

### Tool Not Found

```bash
# List available tools
curl -X POST http://localhost:8080/tools/list | jq '.tools[].name'
```

### Slow Responses

- Check database connection
- Verify PM provider availability
- Check network latency

## 🔗 Related Documentation

- [PM MCP Server Architecture](PM_MCP_SERVER_ARCHITECTURE.md)
- [PM MCP Server Status](PM_MCP_SERVER_STATUS.md)
- [PM MCP Server README](../mcp_server/README.md)

## 📝 Example Use Cases

### 1. Web Dashboard

Build a web dashboard that displays PM data in real-time:

```typescript
// Fetch and display projects
async function loadProjects() {
  const result = await callTool('list_projects', {});
  const projects = parseToolResult(result);
  displayProjects(projects);
}

// Fetch and display tasks
async function loadMyTasks() {
  const result = await callTool('list_my_tasks', {});
  const tasks = parseToolResult(result);
  displayTasks(tasks);
}
```

### 2. Slack Bot

Integrate with Slack to query PM data:

```python
from slack_bolt.async_app import AsyncApp

app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])

@app.command("/pm-tasks")
async def handle_tasks(ack, command, respond):
    await ack()
    
    # Call PM MCP Server
    result = await call_tool("list_my_tasks", {})
    tasks = parse_result(result)
    
    await respond(format_tasks_message(tasks))
```

### 3. CI/CD Integration

Query PM data in CI/CD pipelines:

```bash
#!/bin/bash
# Check if all tasks in sprint are completed

RESULT=$(curl -s -X POST http://localhost:8080/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool":"get_sprint","arguments":{"sprint_id":"sprint-123"}}')

COMPLETED=$(echo $RESULT | jq '.result[0].text' | grep "Completed")

if [ -z "$COMPLETED" ]; then
  echo "❌ Sprint not completed"
  exit 1
fi

echo "✅ Sprint completed"
```

---

**Last Updated**: 2025-01-15  
**Version**: 0.1.0

