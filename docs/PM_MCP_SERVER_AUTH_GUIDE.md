# PM MCP Server - Authentication & Authorization Guide

## 🔐 Overview

The PM MCP Server includes comprehensive authentication and authorization features to secure PM operations and control access based on user roles and permissions.

## 🎯 Features

- **Token-Based Authentication**: Secure Bearer token authentication
- **Role-Based Access Control (RBAC)**: Pre-defined roles with hierarchical permissions
- **Granular Permissions**: Fine-grained control over operations
- **User Management**: Create, update, and manage users
- **Token Lifecycle**: Token generation, validation, and revocation
- **Audit Logging**: Track authentication and authorization events

## 👥 Roles

### Built-in Roles

| Role | Description | Use Case |
|------|-------------|----------|
| **Admin** | Full access to all operations | System administrators |
| **PM** | Project management operations | Project managers |
| **Developer** | Read/write access to tasks, projects | Development team |
| **QC** | QC-specific operations | QA/Testing team |
| **Viewer** | Read-only access | Stakeholders, observers |
| **Agent** | Configurable AI agent access | AI agents (DeerFlow, etc.) |

### Role Permissions

```python
# Admin
- All permissions (admin:all)

# PM (Project Manager)
- project:read, project:write
- task:read, task:write, task:delete, task:assign
- sprint:read, sprint:write, sprint:manage
- epic:read, epic:write
- user:read
- analytics:read

# Developer
- project:read
- task:read, task:write, task:assign
- sprint:read
- epic:read
- user:read
- analytics:read

# QC
- project:read
- task:read, task:write (create defects)
- sprint:read
- user:read
- analytics:read

# Viewer
- project:read
- task:read
- sprint:read
- epic:read
- user:read
- analytics:read

# Agent
- Configurable (default: developer permissions)
```

## 🚀 Quick Start

### 1. Start Server with Authentication

```bash
# HTTP transport with auth enabled (default)
uv run python scripts/run_pm_mcp_server.py --transport http --port 8080

# Disable auth for testing
uv run python scripts/run_pm_mcp_server.py --transport http --port 8080 --no-auth
```

### 2. Generate Authentication Token

```bash
# Get token for admin user
curl -X POST http://localhost:8080/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "expires_in_hours": 24}'

# Response:
# {
#   "token": "abc123...",
#   "user_id": "admin-001",
#   "username": "admin",
#   "role": "admin",
#   "expires_in_hours": 24
# }
```

### 3. Use Token in Requests

```bash
# Set token as environment variable
export PM_TOKEN="your-token-here"

# Use token in requests
curl -H "Authorization: Bearer $PM_TOKEN" \
  http://localhost:8080/projects
```

## 🔑 Default Users

The server comes with pre-configured users for testing:

| Username | Role | Email |
|----------|------|-------|
| `admin` | Admin | admin@pm-mcp.local |
| `developer` | Developer | dev@pm-mcp.local |
| `viewer` | Viewer | viewer@pm-mcp.local |
| `deerflow-agent` | Agent | agent@pm-mcp.local |

## 📡 Authentication API

### Generate Token

```http
POST /auth/token
Content-Type: application/json

{
  "username": "admin",
  "expires_in_hours": 24
}
```

**Response:**
```json
{
  "token": "abc123...",
  "user_id": "admin-001",
  "username": "admin",
  "role": "admin",
  "expires_in_hours": 24
}
```

### Check Authentication Status

```http
GET /auth/check
Authorization: Bearer <token>
```

**Response:**
```json
{
  "authenticated": true,
  "user": {
    "id": "admin-001",
    "username": "admin",
    "role": "admin"
  }
}
```

### Get Current User Info

```http
GET /auth/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "admin-001",
  "username": "admin",
  "email": "admin@pm-mcp.local",
  "role": "admin",
  "permissions": ["admin:all"],
  "is_active": true,
  "created_at": "2025-01-15T10:00:00",
  "last_login": "2025-01-15T12:00:00"
}
```

### Revoke Token

```http
POST /auth/revoke
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "Token revoked successfully"
}
```

### List Users (Admin Only)

```http
GET /auth/users
Authorization: Bearer <admin-token>
```

### Create User (Admin Only)

```http
POST /auth/users
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "username": "newuser",
  "email": "newuser@example.com",
  "role": "developer"
}
```

### Get Auth Statistics (Admin Only)

```http
GET /auth/stats
Authorization: Bearer <admin-token>
```

**Response:**
```json
{
  "total_users": 4,
  "active_users": 4,
  "total_tokens": 10,
  "active_tokens": 5,
  "users_by_role": {
    "admin": 1,
    "developer": 1,
    "viewer": 1,
    "agent": 1
  }
}
```

## 🔧 Usage Examples

### Python httpx

```python
import httpx
import asyncio

BASE_URL = "http://localhost:8080"

async def main():
    async with httpx.AsyncClient() as client:
        # 1. Get token
        response = await client.post(
            f"{BASE_URL}/auth/token",
            json={"username": "admin", "expires_in_hours": 24}
        )
        token = response.json()["token"]
        
        # 2. Set auth header
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Make authenticated requests
        response = await client.get(
            f"{BASE_URL}/projects",
            headers=headers
        )
        projects = response.json()
        print(f"Projects: {projects['count']}")
        
        # 4. Check auth status
        response = await client.get(
            f"{BASE_URL}/auth/check",
            headers=headers
        )
        print(f"Auth status: {response.json()}")

asyncio.run(main())
```

### JavaScript/TypeScript

```typescript
const BASE_URL = 'http://localhost:8080';

async function main() {
  // 1. Get token
  const tokenResponse = await fetch(`${BASE_URL}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: 'admin',
      expires_in_hours: 24
    })
  });
  
  const { token } = await tokenResponse.json();
  
  // 2. Make authenticated requests
  const projectsResponse = await fetch(`${BASE_URL}/projects`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const projects = await projectsResponse.json();
  console.log(`Projects: ${projects.count}`);
}

main();
```

### DeerFlow Integration

```python
from src.tools import configure_pm_mcp_client, get_pm_mcp_tools

# Configure with authentication
configure_pm_mcp_client(
    transport="sse",
    url="http://localhost:8080",
    auth_token="your-token-here"  # Add token
)

# Load tools (will use token for all requests)
pm_tools = await get_pm_mcp_tools()
```

## 🔒 Security Best Practices

### 1. Token Management

```bash
# Generate short-lived tokens for production
curl -X POST http://localhost:8080/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "expires_in_hours": 1}'

# Rotate tokens regularly
# Revoke old tokens when done
curl -X POST http://localhost:8080/auth/revoke \
  -H "Authorization: Bearer $OLD_TOKEN"
```

### 2. Environment Variables

```bash
# Store tokens securely
export PM_MCP_TOKEN="your-token-here"

# Use in scripts
curl -H "Authorization: Bearer $PM_MCP_TOKEN" \
  http://localhost:8080/projects
```

### 3. Role-Based Access

```python
# Create users with appropriate roles
# Admin for system operations
# Developer for development team
# Viewer for read-only access
# Agent for AI agents

# Don't use admin tokens for regular operations
```

### 4. HTTPS in Production

```bash
# Always use HTTPS in production
# Configure SSL/TLS certificates
# Use secure token storage
```

## 🛡️ Permission System

### Tool Permissions

Each tool requires specific permissions:

```python
# Project tools
list_projects -> project:read
create_project -> project:write
delete_project -> project:delete

# Task tools
list_my_tasks -> task:read
create_task -> task:write
assign_task -> task:assign

# Sprint tools
list_sprints -> sprint:read
start_sprint -> sprint:manage

# Analytics tools
burndown_chart -> analytics:read
```

### Custom Permissions

```python
# Create user with custom permissions
curl -X POST http://localhost:8080/auth/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "custom-agent",
    "email": "agent@example.com",
    "role": "agent",
    "permissions": [
      "project:read",
      "task:read",
      "task:write"
    ]
  }'
```

## 🐛 Troubleshooting

### 401 Unauthorized

```bash
# Check if token is valid
curl http://localhost:8080/auth/check \
  -H "Authorization: Bearer $TOKEN"

# Generate new token if expired
curl -X POST http://localhost:8080/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin"}'
```

### 403 Forbidden

```bash
# Check user permissions
curl http://localhost:8080/auth/me \
  -H "Authorization: Bearer $TOKEN"

# User doesn't have required permissions
# Contact admin to update role/permissions
```

### Missing Authorization Header

```bash
# Always include Authorization header
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/projects

# Not just:
curl http://localhost:8080/projects
```

## 📊 Monitoring

### Check Auth Stats

```bash
# Get authentication statistics
curl http://localhost:8080/auth/stats \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Audit Logging

```bash
# Check server logs for auth events
tail -f logs/pm_mcp_server.log | grep -i auth
```

## 🔗 Related Documentation

- [PM MCP Server Architecture](PM_MCP_SERVER_ARCHITECTURE.md)
- [PM MCP Server HTTP Guide](PM_MCP_SERVER_HTTP_GUIDE.md)
- [PM MCP Server SSE Guide](PM_MCP_SERVER_SSE_GUIDE.md)
- [DeerFlow Integration](DEERFLOW_MCP_INTEGRATION.md)

---

**Last Updated**: 2025-01-15  
**Version**: 1.0.0

