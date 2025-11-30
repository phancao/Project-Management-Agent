# PM Service Implementation Plan

## Overview

Extract PM Handler logic into a dedicated microservice to reduce Cursor context and token usage.

**Goal:** Reduce token usage by 50-70% when working on PM features while maintaining performance.

**Timeline:** 2-3 weeks

---

## Phase 1: Create PM Service Foundation (Days 1-2)

### 1.1 Create Directory Structure
```
pm_service/
├── __init__.py
├── main.py                 # FastAPI application
├── config.py               # Configuration management
├── models/
│   ├── __init__.py
│   ├── requests.py         # Request models
│   └── responses.py        # Response models
├── handlers/
│   ├── __init__.py
│   └── pm_handler.py       # Unified PM Handler
├── providers/              # Copy from pm_providers/
│   ├── __init__.py
│   ├── base.py
│   ├── factory.py
│   ├── models.py
│   ├── openproject_v13.py
│   ├── jira.py
│   └── clickup.py
├── database/
│   ├── __init__.py
│   ├── connection.py
│   └── models.py
├── routers/
│   ├── __init__.py
│   ├── projects.py
│   ├── tasks.py
│   ├── sprints.py
│   ├── users.py
│   └── analytics.py
├── Dockerfile
└── requirements.txt
```

### 1.2 Tasks
- [ ] Create `pm_service/` directory
- [ ] Copy `pm_providers/` to `pm_service/providers/`
- [ ] Create `pm_service/main.py` with FastAPI app
- [ ] Create `pm_service/config.py` for configuration
- [ ] Create database models (copy from mcp_server)
- [ ] Create Dockerfile for PM Service
- [ ] Add PM Service to `docker-compose.yml`

### 1.3 Deliverables
- PM Service running on port 8001
- Health check endpoint working
- Basic project structure in place

---

## Phase 2: Implement Core API Endpoints (Days 3-5)

### 2.1 Projects API
```python
GET  /api/v1/projects                    # List all projects
GET  /api/v1/projects/{project_id}       # Get project details
POST /api/v1/projects                    # Create project
PUT  /api/v1/projects/{project_id}       # Update project
```

### 2.2 Tasks API
```python
GET  /api/v1/tasks                       # List tasks (with filters)
GET  /api/v1/tasks/{task_id}             # Get task details
POST /api/v1/tasks                       # Create task
PUT  /api/v1/tasks/{task_id}             # Update task
POST /api/v1/tasks/{task_id}/comments    # Add comment
POST /api/v1/tasks/{task_id}/time        # Log time
```

### 2.3 Sprints API
```python
GET  /api/v1/sprints                     # List sprints
GET  /api/v1/sprints/{sprint_id}         # Get sprint details
GET  /api/v1/sprints/{sprint_id}/tasks   # Get sprint tasks
```

### 2.4 Users API
```python
GET  /api/v1/users                       # List users
GET  /api/v1/users/{user_id}             # Get user details
GET  /api/v1/users/{user_id}/workload    # Get user workload
```

### 2.5 Analytics API
```python
GET  /api/v1/analytics/burndown          # Burndown chart data
GET  /api/v1/analytics/velocity          # Velocity chart data
GET  /api/v1/analytics/sprint-report     # Sprint report
GET  /api/v1/analytics/project-health    # Project health metrics
```

### 2.6 Providers API
```python
GET  /api/v1/providers                   # List configured providers
POST /api/v1/providers                   # Add provider
PUT  /api/v1/providers/{id}              # Update provider
DELETE /api/v1/providers/{id}            # Remove provider
POST /api/v1/providers/sync              # Sync from backend
```

### 2.7 Tasks
- [ ] Create `routers/projects.py`
- [ ] Create `routers/tasks.py`
- [ ] Create `routers/sprints.py`
- [ ] Create `routers/users.py`
- [ ] Create `routers/analytics.py`
- [ ] Create `routers/providers.py`
- [ ] Create unified `handlers/pm_handler.py`
- [ ] Add request/response models
- [ ] Add error handling
- [ ] Add logging

### 2.8 Deliverables
- All CRUD endpoints working
- Swagger docs at `/docs`
- Error handling in place

---

## Phase 3: Create PM Service Client (Days 6-7)

### 3.1 Python Client Library
```python
# pm_service/client.py
class PMServiceClient:
    """Client for PM Service API."""
    
    def __init__(self, base_url: str = "http://pm_service:8001"):
        self.base_url = base_url
        self.session = httpx.AsyncClient()
    
    async def list_projects(self, user_id: str = None) -> List[PMProject]:
        """List projects."""
        pass
    
    async def get_project(self, project_id: str) -> PMProject:
        """Get project details."""
        pass
    
    async def list_tasks(
        self, 
        project_id: str = None,
        sprint_id: str = None,
        assignee_id: str = None
    ) -> List[PMTask]:
        """List tasks with filters."""
        pass
    
    # ... more methods
```

### 3.2 Tasks
- [ ] Create `pm_service/client.py`
- [ ] Add async HTTP client (httpx)
- [ ] Add retry logic with exponential backoff
- [ ] Add connection pooling
- [ ] Add timeout handling
- [ ] Add error mapping
- [ ] Create shared package structure

### 3.3 Deliverables
- Python client library ready for use
- Retry and error handling in place

---

## Phase 4: Migrate MCP Server (Days 8-10)

### 4.1 Update MCP Server Tools
Replace direct `MCPPMHandler` calls with `PMServiceClient` calls.

**Before:**
```python
# mcp_server/tools/projects.py
class ListProjectsTool(ReadTool):
    async def execute(self):
        handler = MCPPMHandler(db_session)
        return await handler.list_projects()
```

**After:**
```python
# mcp_server/tools/projects.py
class ListProjectsTool(ReadTool):
    async def execute(self):
        client = PMServiceClient()
        return await client.list_projects()
```

### 4.2 Tasks
- [ ] Add `PMServiceClient` to MCP Server
- [ ] Update `ListProjectsTool`
- [ ] Update `GetProjectTool`
- [ ] Update `ListTasksTool`
- [ ] Update `GetTaskTool`
- [ ] Update `CreateTaskTool`
- [ ] Update `UpdateTaskTool`
- [ ] Update `ListSprintsTool`
- [ ] Update `GetSprintTool`
- [ ] Update `SprintReportTool`
- [ ] Update `BurndownChartTool`
- [ ] Update `VelocityChartTool`
- [ ] Update `ProjectHealthTool`
- [ ] Update `ListUsersTool`
- [ ] Update `GetUserTool`
- [ ] Remove old `MCPPMHandler`
- [ ] Update tests

### 4.3 Deliverables
- MCP Server using PM Service
- All tools working correctly
- Tests passing

---

## Phase 5: Migrate Backend API (Days 11-13)

### 5.1 Update Backend Endpoints
Replace direct `PMHandler` calls with `PMServiceClient` calls.

**Before:**
```python
# src/server/app.py
@app.get("/api/pm/projects")
async def list_projects():
    handler = PMHandler(db_session)
    return await handler.list_projects()
```

**After:**
```python
# src/server/app.py
@app.get("/api/pm/projects")
async def list_projects():
    client = PMServiceClient()
    return await client.list_projects()
```

### 5.2 Tasks
- [ ] Add `PMServiceClient` to Backend
- [ ] Update project endpoints
- [ ] Update task endpoints
- [ ] Update sprint endpoints
- [ ] Update user endpoints
- [ ] Update analytics endpoints
- [ ] Remove old `PMHandler`
- [ ] Update tests

### 5.3 Deliverables
- Backend using PM Service
- All endpoints working correctly
- Tests passing

---

## Phase 6: Cleanup and Optimization (Days 14-15)

### 6.1 Remove Old Code
- [ ] Remove `src/server/pm_handler.py`
- [ ] Remove `mcp_server/pm_handler.py`
- [ ] Remove duplicate `pm_providers/` references
- [ ] Update imports across codebase
- [ ] Remove unused dependencies

### 6.2 Add Caching (Optional)
- [ ] Add Redis caching for frequently accessed data
- [ ] Cache project list (TTL: 5 min)
- [ ] Cache sprint list (TTL: 5 min)
- [ ] Cache user list (TTL: 10 min)

### 6.3 Add Monitoring
- [ ] Add request logging
- [ ] Add performance metrics
- [ ] Add health check dashboard
- [ ] Add alerting for errors

### 6.4 Documentation
- [ ] Update README.md
- [ ] Update architecture docs
- [ ] Add PM Service API docs
- [ ] Update deployment guide

### 6.5 Deliverables
- Clean codebase
- Updated documentation
- Monitoring in place

---

## Docker Compose Changes

```yaml
# Add to docker-compose.yml

  # PM Service - Dedicated service for PM provider interactions
  pm_service:
    container_name: pm-service
    build:
      context: ./pm_service
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://mcp_user:mcp_password@mcp-postgres:5432/mcp_server
      - LOG_LEVEL=${PM_SERVICE_LOG_LEVEL:-INFO}
      - OPENPROJECT_URL=${OPENPROJECT_URL:-http://host.docker.internal:8083}
    ports:
      - "8001:8001"
    depends_on:
      mcp_postgres:
        condition: service_healthy
    volumes:
      - ./pm_service:/app
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped

  # Update api service
  api:
    environment:
      - PM_SERVICE_URL=http://pm_service:8001
    depends_on:
      - pm_service

  # Update mcp_server service
  pm_mcp_server:
    environment:
      - PM_SERVICE_URL=http://pm_service:8001
    depends_on:
      - pm_service
```

---

## Testing Strategy

### Unit Tests
- Test PM Service endpoints independently
- Test client library methods
- Mock external PM APIs

### Integration Tests
- Test Backend → PM Service → OpenProject flow
- Test MCP Server → PM Service → OpenProject flow
- Test error handling and retries

### Performance Tests
- Measure latency before/after migration
- Load test PM Service
- Verify no performance regression

---

## Rollback Plan

If issues arise:
1. Revert `docker-compose.yml` changes
2. Restore old `PMHandler` and `MCPPMHandler`
3. Remove PM Service container
4. Deploy previous version

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Token reduction | 50-70% | Compare Cursor token usage before/after |
| Latency increase | <5ms | Measure API response times |
| Error rate | <0.1% | Monitor PM Service errors |
| Test coverage | >80% | Run coverage report |

---

## Current Status

### Phase 1: Create PM Service Foundation ✅ COMPLETE
- [x] Created `pm_service/` directory structure
- [x] Copied provider code
- [x] Created FastAPI app (port 8001)
- [x] Added to Docker Compose
- [x] Tested health endpoint

### Phase 2: Create PM Service Client ✅ COMPLETE
- [x] Created `pm_service/client/async_client.py`
- [x] Created `pm_service/client/client.py` (sync wrapper)
- [x] Added retry logic with exponential backoff
- [x] Created new MCP tools using PM Service client

### Phase 3: Migrate MCP Server 🔄 IN PROGRESS
- [x] Created `mcp_server/tools/pm_service_tools/`
- [x] Added PM_SERVICE_URL to MCP Server
- [ ] Switch MCP Server to use new tools (optional - can run both)

### Phase 4: Migrate Backend API
- [ ] Add PM_SERVICE_URL to Backend
- [ ] Update Backend endpoints to use client

### Phase 5: Cleanup
- [ ] Remove old PMHandler
- [ ] Remove old MCPPMHandler
- [ ] Update documentation

---

## Commands

```bash
# Start PM Service
docker-compose up -d pm_service

# View logs
docker logs -f pm-service

# Test health
curl http://localhost:8001/health

# Run tests
cd pm_service && pytest

# Build image
docker build -t pm-service ./pm_service
```

