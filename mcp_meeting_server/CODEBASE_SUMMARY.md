# MCP Meeting Server - Codebase Summary

## Overview
MCP (Model Context Protocol) server that exposes meeting processing tools to AI agents.

## Purpose
Allow Claude, GPT, and other AI agents to process meetings via standardized tool calls.

---

## Module Structure

```
mcp_meeting_server/
├── __init__.py          # Package exports
├── config.py            # MeetingServerConfig
├── server.py            # MeetingMCPServer main class
├── tools/
│   └── __init__.py      # Tool implementations
└── transports/
    ├── sse.py           # Server-Sent Events transport
    └── http.py          # HTTP REST transport
```

---

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `upload_meeting` | Upload audio/video for processing |
| `process_meeting` | Transcribe and analyze uploaded meeting |
| `analyze_transcript` | Analyze text transcript directly |
| `get_meeting_summary` | Get summary for a meeting |
| `list_action_items` | List extracted action items |
| `create_tasks_from_meeting` | Create PM tasks from action items |
| `list_meetings` | List all processed meetings |

---

## Running the Server

```bash
# SSE transport (for Claude Desktop)
python scripts/run_meeting_mcp_server.py --transport sse --port 8082

# HTTP transport (for REST API)
python scripts/run_meeting_mcp_server.py --transport http --port 8082

# stdio transport (for Claude Desktop integration)
python scripts/run_meeting_mcp_server.py --transport stdio
```

---

## Configuration

```python
from mcp_meeting_server.config import MeetingServerConfig

config = MeetingServerConfig(
    transport="sse",
    host="0.0.0.0",
    port=8082,
    enable_auth=True,
)
```

Environment variables:
- `MEETING_SERVER_PORT` - Port number
- `MEETING_SERVER_TRANSPORT` - sse/http/stdio
- `MEETING_DATABASE_URL` - SQLite database path

---

## Dependencies
- `meeting_agent/` - Core processing
- `shared/handlers/` - HandlerContext, HandlerResult
- `mcp` - MCP SDK
- `fastapi`, `uvicorn` - HTTP/SSE server
