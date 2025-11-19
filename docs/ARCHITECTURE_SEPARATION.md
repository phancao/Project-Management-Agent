# Architecture: Backend Server vs PM MCP Server Separation

## Overview

The system is now architected with **two separate services**:

1. **Backend Server (API)** - Main FastAPI application
2. **PM MCP Server** - Dedicated MCP protocol server

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Applications                      │
│  (Web UI, Claude Desktop, LangChain Agents, etc.)          │
└──────────────┬──────────────────────────┬──────────────────┘
               │                          │
               │                          │
    ┌──────────▼──────────┐    ┌─────────▼──────────┐
    │   Backend Server    │    │   PM MCP Server    │
    │   (FastAPI)         │    │   (MCP Protocol)   │
    │   Port: 8000        │    │   Port: 8080       │
    │                     │    │                    │
    │  - Web API          │    │  - MCP Tools       │
    │  - Chat Stream      │    │  - 53 PM Tools     │
    │  - PM REST API      │    │  - SSE/HTTP/stdio  │
    │  - MCP Client       │◄───┤  - Tool Execution  │
    └──────────┬──────────┘    └─────────┬──────────┘
               │                          │
               │                          │
    ┌──────────▼──────────────────────────▼──────────┐
    │            Shared Database (PostgreSQL)          │
    │         - PM Providers Configuration            │
    │         - Projects, Tasks, Sprints, etc.        │
    └─────────────────────────────────────────────────┘
```

## Service Responsibilities

### Backend Server (API Service)

**Responsibilities:**
- Web API endpoints (`/api/*`)
- Chat streaming (`/api/chat/stream`)
- PM REST API (`/api/pm/*`)
- MCP client functionality (connects to MCP servers)
- User authentication & authorization
- Session management
- Graph workflow execution

**Port:** 8000

**Docker Service:** `api`

### PM MCP Server

**Responsibilities:**
- MCP protocol implementation
- 53 PM tools (projects, tasks, sprints, epics, users, analytics)
- Tool execution and validation
- MCP transport handling (SSE/HTTP/stdio)
- Direct database access for PM operations

**Port:** 8080

**Docker Service:** `pm_mcp_server`

## Communication Pattern

### How They Connect

1. **Backend Server → PM MCP Server:**
   - Backend acts as **MCP Client**
   - Connects via SSE/HTTP transport
   - Uses `MultiServerMCPClient` from `langchain-mcp-adapters`
   - URL: `http://pm_mcp_server:8080/sse` (Docker) or `http://localhost:8080/sse` (local)

2. **Shared Database:**
   - Both services connect to the same PostgreSQL database
   - Backend: For PM REST API and configuration
   - PM MCP Server: For tool execution

### Configuration

**Backend Server Environment Variables:**
```bash
PM_MCP_SERVER_URL=http://pm_mcp_server:8080/sse  # Docker service name
PM_MCP_TRANSPORT=sse                              # Transport type
```

**PM MCP Server Environment Variables:**
```bash
DATABASE_URL=postgresql://pm_user:pm_password@postgres:5432/project_management
MCP_TRANSPORT=sse
MCP_HOST=0.0.0.0
MCP_PORT=8080
```

## Deployment Scenarios

### Scenario 1: Docker Compose (Recommended for Production)

```yaml
services:
  api:              # Backend server
    depends_on:
      - pm_mcp_server
  
  pm_mcp_server:    # MCP server
    depends_on:
      - postgres
```

**Benefits:**
- Automatic service discovery
- Health checks and restart policies
- Resource isolation
- Easy scaling

### Scenario 2: Standalone (Development)

**Backend Server:**
```bash
uv run python server.py
```

**PM MCP Server:**
```bash
uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080
```

**Configuration:**
```bash
export PM_MCP_SERVER_URL=http://localhost:8080/sse
export PM_MCP_TRANSPORT=sse
```

### Scenario 3: Hybrid (Backend in Docker, MCP Local)

**Backend Server:**
- Runs in Docker
- Connects to local MCP server via `http://host.docker.internal:8080/sse`

**PM MCP Server:**
- Runs locally for development/debugging

## Benefits of Separation

### 1. **Isolation**
- MCP server failures don't crash the backend
- Independent error handling and recovery
- Separate logging and monitoring

### 2. **Scalability**
- Scale MCP server independently based on tool usage
- Scale backend based on API traffic
- Run multiple MCP server instances for load balancing

### 3. **Resource Management**
- Dedicated CPU/memory for each service
- Better resource utilization
- Predictable performance

### 4. **Deployment Flexibility**
- Update MCP server without restarting backend
- Deploy to different servers/regions
- Use different scaling strategies

### 5. **Development**
- Develop and test MCP server independently
- Faster iteration cycles
- Easier debugging

## Migration Path

### Current State (Before Separation)
- PM MCP Server runs as subprocess via stdio
- Backend spawns MCP server on demand
- Tightly coupled

### Target State (After Separation)
- PM MCP Server runs as independent service
- Backend connects via HTTP/SSE
- Loosely coupled

### Migration Steps

1. **Deploy PM MCP Server in Docker:**
   ```bash
   docker-compose up -d pm_mcp_server
   ```

2. **Update Backend Configuration:**
   ```bash
   export PM_MCP_SERVER_URL=http://pm_mcp_server:8080/sse
   export PM_MCP_TRANSPORT=sse
   ```

3. **Verify Connection:**
   ```bash
   curl http://localhost:8080/health
   ```

4. **Test Integration:**
   - Send chat request with PM tools
   - Verify tools are available
   - Check logs for connection status

## Monitoring

### Backend Server Metrics
- API request rate
- Response times
- Error rates
- MCP connection status

### PM MCP Server Metrics
- Tool call rate
- Tool execution time
- Error rates
- Active connections

### Shared Metrics
- Database connection pool
- Query performance
- Cache hit rates

## Troubleshooting

### Backend Can't Connect to MCP Server

1. **Check MCP Server is Running:**
   ```bash
   docker-compose ps pm_mcp_server
   curl http://localhost:8080/health
   ```

2. **Check Network Connectivity:**
   ```bash
   docker-compose exec api curl http://pm_mcp_server:8080/health
   ```

3. **Check Environment Variables:**
   ```bash
   docker-compose exec api env | grep PM_MCP
   ```

4. **Check Logs:**
   ```bash
   docker-compose logs pm_mcp_server
   docker-compose logs api | grep PM_MCP
   ```

### MCP Tools Not Available

1. **Verify Tool Registration:**
   ```bash
   curl http://localhost:8080/tools/list
   ```

2. **Check Backend MCP Configuration:**
   - Verify `PM_MCP_SERVER_URL` is set
   - Check MCP settings in chat request

3. **Check Database Connection:**
   - Both services need database access
   - Verify `DATABASE_URL` is correct

## Best Practices

1. **Always use SSE transport in Docker** (better than stdio)
2. **Set resource limits** for both services
3. **Enable health checks** for automatic recovery
4. **Use service names** for internal communication
5. **Monitor both services** independently
6. **Keep versions in sync** when possible
7. **Use environment variables** for configuration
8. **Test locally** before deploying to production

