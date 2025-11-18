# PM MCP Server - HTTP REST API Guide

## 🌐 Overview

The HTTP transport provides a standard REST API for accessing PM operations. Perfect for general integration, webhooks, and third-party applications.

## 🚀 Quick Start

### 1. Start the HTTP Server

```bash
# Start on default port (8080)
uv run python scripts/run_pm_mcp_server.py --transport http

# Start on custom port
uv run python scripts/run_pm_mcp_server.py --transport http --port 8082 --host 0.0.0.0
```

### 2. Access API Documentation

Open your browser to:
- **Swagger UI**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`

### 3. Test the API

```bash
# Server info
curl http://localhost:8080/

# Health check
curl http://localhost:8080/health

# List all tools
curl http://localhost:8080/tools

# List projects
curl http://localhost:8080/projects

# List my tasks
curl http://localhost:8080/tasks/my
```

## 📡 API Endpoints

### Core Endpoints

#### Get Server Info
```http
GET /
```

Response:
```json
{
  "name": "pm-server",
  "version": "0.1.0",
  "transport": "http",
  "status": "running",
  "tools_count": 51,
  "providers_count": 3
}
```

#### Health Check
```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "providers": 3,
  "tools": 51,
  "categories": ["projects", "tasks", "sprints", "epics", "users", "analytics", "task_interactions"]
}
```

### Tool Endpoints

#### List All Tools
```http
GET /tools?category=projects
```

Response:
```json
[
  {
    "name": "list_projects",
    "description": "List all accessible projects...",
    "category": "projects",
    "parameters": {}
  },
  ...
]
```

#### List Tool Categories
```http
GET /tools/categories
```

Response:
```json
{
  "categories": {
    "projects": {
      "name": "projects",
      "tool_count": 6,
      "tools": ["list_projects", "get_project", ...]
    },
    ...
  },
  "total_categories": 7,
  "total_tools": 51
}
```

#### Call a Tool
```http
POST /tools/call
Content-Type: application/json

{
  "tool": "list_projects",
  "arguments": {
    "provider_id": "openproject-1",
    "limit": 10
  }
}
```

Response:
```json
{
  "tool": "list_projects",
  "result": [
    {
      "type": "text",
      "text": "Found 5 projects:\n..."
    }
  ],
  "success": true,
  "error": null
}
```

### Project Endpoints

#### List Projects
```http
GET /projects?provider_id=openproject-1&search=web&limit=10
```

#### Get Project
```http
GET /projects/{project_id}
```

### Task Endpoints

#### List My Tasks
```http
GET /tasks/my?status=open&provider_id=jira-1
```

#### List Project Tasks
```http
GET /projects/{project_id}/tasks?status=in_progress&assignee=user-123
```

#### Get Task
```http
GET /tasks/{task_id}
```

### Sprint Endpoints

#### List Sprints
```http
GET /projects/{project_id}/sprints?status=active
```

#### Get Sprint
```http
GET /sprints/{sprint_id}
```

### User Endpoints

#### List Users
```http
GET /users?project_id=proj-123&provider_id=openproject-1
```

#### Get Current User
```http
GET /users/me?provider_id=openproject-1
```

### Analytics Endpoints

#### Get Burndown Chart
```http
GET /analytics/burndown/{sprint_id}
```

#### Get Velocity Chart
```http
GET /analytics/velocity/{project_id}?sprint_count=5
```

## 🔧 Usage Examples

### cURL Examples

```bash
# List all projects
curl http://localhost:8080/projects

# Get specific project
curl http://localhost:8080/projects/proj-123

# List my tasks
curl http://localhost:8080/tasks/my

# Call a tool
curl -X POST http://localhost:8080/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "create_task",
    "arguments": {
      "project_id": "proj-123",
      "subject": "New task",
      "description": "Task description"
    }
  }'

# Get burndown chart
curl http://localhost:8080/analytics/burndown/sprint-456
```

### Python httpx Example

```python
import httpx
import asyncio

BASE_URL = "http://localhost:8080"

async def main():
    async with httpx.AsyncClient() as client:
        # Get server info
        response = await client.get(f"{BASE_URL}/")
        print(response.json())
        
        # List projects
        response = await client.get(f"{BASE_URL}/projects")
        projects = response.json()
        print(f"Found {projects['count']} projects")
        
        # List my tasks
        response = await client.get(f"{BASE_URL}/tasks/my")
        tasks = response.json()
        print(f"You have {tasks['count']} tasks")
        
        # Call a tool
        response = await client.post(
            f"{BASE_URL}/tools/call",
            json={
                "tool": "get_project",
                "arguments": {"project_id": "proj-123"}
            }
        )
        result = response.json()
        print(result)

asyncio.run(main())
```

### Python requests Example

```python
import requests

BASE_URL = "http://localhost:8080"

# List projects
response = requests.get(f"{BASE_URL}/projects")
projects = response.json()
print(f"Projects: {projects['count']}")

# Create task
response = requests.post(
    f"{BASE_URL}/tools/call",
    json={
        "tool": "create_task",
        "arguments": {
            "project_id": "proj-123",
            "subject": "New feature",
            "description": "Implement new feature"
        }
    }
)
result = response.json()
if result['success']:
    print("✅ Task created!")
else:
    print(f"❌ Error: {result['error']}")
```

### JavaScript/TypeScript Example

```typescript
const BASE_URL = 'http://localhost:8080';

// List projects
async function listProjects() {
  const response = await fetch(`${BASE_URL}/projects`);
  const data = await response.json();
  console.log(`Found ${data.count} projects`);
  return data.projects;
}

// Create task
async function createTask(projectId: string, subject: string) {
  const response = await fetch(`${BASE_URL}/tools/call`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tool: 'create_task',
      arguments: {
        project_id: projectId,
        subject: subject,
        description: 'Created via API'
      }
    })
  });
  
  const result = await response.json();
  return result;
}

// Get burndown chart
async function getBurndown(sprintId: string) {
  const response = await fetch(`${BASE_URL}/analytics/burndown/${sprintId}`);
  const data = await response.json();
  return data;
}

// Usage
const projects = await listProjects();
const task = await createTask('proj-123', 'New task');
const burndown = await getBurndown('sprint-456');
```

## 🔐 Security

### Authentication (Future)

```python
# Add Bearer token authentication
headers = {
    "Authorization": "Bearer your-api-token",
    "Content-Type": "application/json"
}

response = requests.get(
    f"{BASE_URL}/projects",
    headers=headers
)
```

### API Key (Future)

```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:8080/projects
```

### Rate Limiting

The server supports rate limiting per IP:
- Default: 100 requests/minute
- Configurable via environment variables

## 📊 OpenAPI/Swagger

### Export OpenAPI Schema

```bash
# Get OpenAPI JSON
curl http://localhost:8080/openapi.json > openapi.json

# Generate client code
openapi-generator-cli generate \
  -i openapi.json \
  -g python \
  -o ./pm-mcp-client
```

### Interactive API Testing

Visit `http://localhost:8080/docs` to:
- Browse all endpoints
- Test API calls interactively
- View request/response schemas
- Download OpenAPI specification

## 🔗 Webhook Integration

### GitHub Actions Example

```yaml
name: Update PM on Deploy

on:
  push:
    branches: [main]

jobs:
  update-pm:
    runs-on: ubuntu-latest
    steps:
      - name: Update task status
        run: |
          curl -X POST ${{ secrets.PM_MCP_URL }}/tools/call \
            -H "Content-Type: application/json" \
            -d '{
              "tool": "update_task_status",
              "arguments": {
                "task_id": "${{ github.event.head_commit.message }}",
                "status": "deployed"
              }
            }'
```

### Zapier/Make.com Integration

1. Create HTTP Request action
2. Set URL: `http://your-server:8080/tools/call`
3. Set Method: POST
4. Set Body:
```json
{
  "tool": "create_task",
  "arguments": {
    "project_id": "{{project_id}}",
    "subject": "{{task_subject}}",
    "description": "{{task_description}}"
  }
}
```

## 🐛 Troubleshooting

### CORS Errors

If you get CORS errors, the server allows all origins by default. Check your request headers.

### 404 Not Found

```bash
# List available endpoints
curl http://localhost:8080/docs

# Check tool exists
curl http://localhost:8080/tools | grep "tool_name"
```

### 500 Internal Server Error

```bash
# Check server logs
tail -f logs/pm_mcp_server.log

# Check health
curl http://localhost:8080/health
```

### Timeout

- Increase request timeout
- Check database connection
- Verify PM provider availability

## 📈 Performance

### Caching

Results are cached for 5 minutes by default:
```python
# Configure cache TTL
config = PMServerConfig(
    cache_ttl=300  # seconds
)
```

### Connection Pooling

The server maintains connection pools to PM providers for optimal performance.

### Monitoring

```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8080/projects

# Monitor with prometheus
curl http://localhost:8080/metrics
```

## 🔗 Related Documentation

- [PM MCP Server Architecture](PM_MCP_SERVER_ARCHITECTURE.md)
- [PM MCP Server SSE Guide](PM_MCP_SERVER_SSE_GUIDE.md)
- [PM MCP Server Status](PM_MCP_SERVER_STATUS.md)

---

**Last Updated**: 2025-01-15  
**Version**: 0.1.0

