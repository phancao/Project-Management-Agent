# 🐞 BugBase MCP Server

The **BugBase MCP Server** is the core backend for the Galaxy AI Self-Improvement System. It enables AI agents (like Antigravity and Cursor) to autonomously discover, investigate, and fix reported bugs.

## 🚀 Features

- **MCP Protocol Implementation**: Exposes tools for listing, retrieving, and updating bugs.
- **PostgreSQL Storage**: Robust data persistence using SQLAlchemy and `pgvector` container.
- **Screenshot Management**: Securely serves captured screenshots to the frontend.
- **SSE Transport**: Server-Sent Events for real-time MCP communication.

## 🛠️ Installation & Setup

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- `uv` or `pip` (for local development)

### Running with Docker (Recommended)

The server is integrated into the main `docker-compose.yml`.

```bash
docker compose up -d bugbase_mcp_server
```

This will start:
1. `bugbase_postgres`: Database on port 5436
2. `bugbase_mcp_server`: API & MCP Server on port 8082

## 🔌 Connecting to AI Agents

To allow your AI assistant to read and fix bugs, you need to connect it to this MCP server.

### Option 1: Antigravity (Google)

1. Open the **Agent Panel** in Antigravity.
2. Click the **"..." menu** (top right) → **MCP Servers**.
3. Click **"Manage MCP Servers"**.
4. Click **"View raw config"**.
5. Add the following configuration to `mcp_config.json`:

```json
{
  "mcpServers": {
    "bugbase": {
      "command": "bash",
      "args": [
        "-c",
        "cd '/absolute/path/to/Project-Management-Agent/bugbase_mcp_server' && python3 stdio_wrapper.py"
      ]
    }
  }
}
```
6. **Important:** Click **"Refresh"** in the Manage MCP Servers view.

### Option 2: Cursor API

Add to your `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "bugbase": {
      "command": "python3",
      "args": ["/absolute/path/to/bugbase_mcp_server/stdio_wrapper.py"]
    }
  }
}
```

## 🧰 Available Tools

The server exposes the following MCP tools to the AI:

| Tool | Description |
|------|-------------|
| `list_bugs` | List bugs with filters (status, severity, limit). |
| `get_bug_details` | Get full details including screenshot path, navigation history, and comments. |
| `update_bug_status` | Change status (`open`, `in_progress`, `fixed`, `closed`). |
| `add_bug_comment` | Add investigation notes or resolution details. |

## 🧪 Development

### Local Setup

```bash
cd bugbase_mcp_server
pip install -r requirements.txt
python server.py
```

### API Documentation

When running locally, full Swagger UI is available at:
`http://localhost:8082/docs`
