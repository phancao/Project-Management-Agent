# PM Service Separation Analysis

## Current Architecture

### Current State
```
┌─────────────────────────────────────────────────────────────┐
│                    Monolithic Codebase                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │  Backend API     │         │   MCP Server      │        │
│  │  (FastAPI)       │         │   (MCP Protocol)  │        │
│  └────────┬──────────┘         └────────┬─────────┘        │
│           │                             │                  │
│           │  PMHandler                   │  MCPPMHandler    │
│           │  (src/server/pm_handler.py)   │  (mcp_server/   │
│           │                             │   pm_handler.py) │
│           └──────────────┬───────────────┘                  │
│                          │                                  │
│              ┌───────────▼───────────┐                      │
│              │   pm_providers/       │                      │
│              │   (Shared Code)       │                      │
│              │   - OpenProject        │                      │
│              │   - JIRA               │                      │
│              │   - ClickUp            │                      │
│              └───────────────────────┘                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Issues with Current Architecture

1. **Context Bloat in Cursor:**
   - Both `PMHandler` and `MCPPMHandler` are in the same codebase
   - Cursor needs to understand both contexts when working on either
   - Increases token usage significantly
   - Makes code navigation more complex

2. **Code Duplication:**
   - `PMHandler` and `MCPPMHandler` have similar logic
   - Both handle provider management, error handling, aggregation
   - ~500+ lines of duplicated logic

3. **Tight Coupling:**
   - Changes to one handler might affect the other
   - Harder to test independently
   - Deployment requires rebuilding entire codebase

## Proposed Solutions

### Option A: Extract PM Service as Separate Microservice ⭐ **RECOMMENDED**

```
┌──────────────────┐         ┌──────────────────┐
│  Backend API     │         │   MCP Server    │
│  (FastAPI)       │         │   (MCP Protocol)│
└────────┬─────────┘         └────────┬───────┘
         │                              │
         │  HTTP/gRPC                   │  HTTP/gRPC
         │                              │
         └──────────┬───────────────────┘
                    │
         ┌───────────▼───────────┐
         │   PM Service API      │
         │   (Dedicated Service) │
         │   - FastAPI/gRPC      │
         │   - Port 8001         │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │   pm_providers/      │
         │   (Shared Library)    │
         └──────────────────────┘
```

**Benefits:**
- ✅ **Reduced Context**: Cursor only needs to understand PM Service when working on PM logic
- ✅ **Single Source of Truth**: One implementation, no duplication
- ✅ **Independent Scaling**: Can scale PM service separately
- ✅ **Clear Boundaries**: Each service has a single responsibility
- ✅ **Easier Testing**: Test PM service independently
- ✅ **Token Savings**: ~50-70% reduction in context when working on PM features

**Implementation:**
1. Create new `pm_service/` directory
2. Move `pm_providers/` into `pm_service/`
3. Create FastAPI service with PM endpoints
4. Both Backend and MCP Server call PM Service via HTTP/gRPC
5. PM Service handles all provider logic

**Trade-offs:**
- ⚠️ Network latency (~1-5ms per call)
- ⚠️ Additional service to maintain
- ⚠️ Need to handle service discovery

---

### Option B: Extract PM Providers as Shared Library

```
┌──────────────────┐         ┌──────────────────┐
│  Backend API     │         │   MCP Server     │
│  (FastAPI)       │         │   (MCP Protocol) │
└────────┬─────────┘         └────────┬─────────┘
         │                              │
         │  Direct Import               │  Direct Import
         │                              │
         └──────────┬───────────────────┘
                    │
         ┌───────────▼───────────┐
         │   pm_providers/       │
         │   (Shared Package)    │
         │   - pip installable    │
         │   - Versioned         │
         └───────────────────────┘
```

**Benefits:**
- ✅ **Code Reuse**: Single implementation
- ✅ **Version Control**: Can version PM providers independently
- ✅ **Reduced Duplication**: No duplicate handler logic

**Drawbacks:**
- ❌ **Still in Same Codebase**: Cursor still sees both handlers
- ❌ **Context Not Reduced**: Token usage remains high
- ❌ **Tight Coupling**: Changes still affect both services

---

### Option C: Keep Current + Better Organization

**Benefits:**
- ✅ **No Migration**: Keep current architecture
- ✅ **Quick Win**: Just reorganize code structure

**Drawbacks:**
- ❌ **No Token Savings**: Context still includes both handlers
- ❌ **Code Duplication**: Still have duplicate logic
- ❌ **Maintenance Burden**: Two implementations to maintain

---

## Recommendation: Option A (PM Service)

### Why Option A?

1. **Token Efficiency:**
   - When working on Backend API → Only see Backend code
   - When working on MCP Server → Only see MCP Server code
   - When working on PM features → Only see PM Service code
   - **Estimated 50-70% token reduction** for typical tasks

2. **Clear Separation of Concerns:**
   - Backend API: Handles web requests, authentication, business logic
   - MCP Server: Handles MCP protocol, tool registration
   - PM Service: Handles all PM provider interactions

3. **Future-Proof:**
   - Easy to add new consumers (CLI, SDK, etc.)
   - Can optimize PM service independently
   - Can use different tech stack if needed

### Implementation Plan

#### Phase 1: Create PM Service (Week 1)
```bash
pm_service/
├── __init__.py
├── main.py              # FastAPI app
├── handlers/
│   └── pm_handler.py    # Unified PM handler
├── providers/           # Move from pm_providers/
│   ├── openproject_v13.py
│   ├── jira.py
│   └── ...
├── models.py
└── Dockerfile
```

#### Phase 2: Migrate Backend (Week 1-2)
- Update Backend API to call PM Service
- Replace `PMHandler` calls with HTTP/gRPC calls
- Add retry logic and error handling

#### Phase 3: Migrate MCP Server (Week 2)
- Update MCP Server to call PM Service
- Replace `MCPPMHandler` calls with HTTP/gRPC calls
- Update tool implementations

#### Phase 4: Cleanup (Week 2-3)
- Remove old `PMHandler` and `MCPPMHandler`
- Update tests
- Update documentation

### API Design (PM Service)

```python
# pm_service/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="PM Service API")

@app.post("/api/v1/projects")
async def list_projects(
    user_id: Optional[str] = None,
    provider_id: Optional[str] = None
) -> List[PMProject]:
    """List projects from PM providers."""
    pass

@app.get("/api/v1/projects/{project_id}")
async def get_project(project_id: str) -> PMProject:
    """Get project details."""
    pass

@app.post("/api/v1/tasks")
async def list_tasks(
    project_id: Optional[str] = None,
    sprint_id: Optional[str] = None,
    assignee_id: Optional[str] = None
) -> List[PMTask]:
    """List tasks."""
    pass

# ... more endpoints
```

### Communication Protocol

**Option 1: HTTP REST (Recommended for simplicity)**
- Easy to debug
- Standard tooling
- ~1-5ms latency (acceptable)

**Option 2: gRPC (For performance)**
- Lower latency (~0.5-2ms)
- Type-safe contracts
- More complex setup

**Recommendation: Start with HTTP REST, migrate to gRPC if needed**

### Docker Compose Update

```yaml
services:
  pm_service:
    build:
      context: ./pm_service
      dockerfile: Dockerfile
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=...
      - OPENAI_API_KEY=...
    volumes:
      - ./pm_service:/app
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      
  api:
    environment:
      - PM_SERVICE_URL=http://pm_service:8001
    depends_on:
      - pm_service
      
  pm_mcp_server:
    environment:
      - PM_SERVICE_URL=http://pm_service:8001
    depends_on:
      - pm_service
```

## Migration Checklist

- [ ] Create `pm_service/` directory structure
- [ ] Move `pm_providers/` to `pm_service/providers/`
- [ ] Create unified `PMHandler` in PM Service
- [ ] Create FastAPI app with PM endpoints
- [ ] Add Dockerfile for PM Service
- [ ] Update `docker-compose.yml`
- [ ] Migrate Backend API to call PM Service
- [ ] Migrate MCP Server to call PM Service
- [ ] Remove old `PMHandler` and `MCPPMHandler`
- [ ] Update tests
- [ ] Update documentation
- [ ] Performance testing
- [ ] Deploy to staging
- [ ] Deploy to production

## Metrics to Track

1. **Token Usage:**
   - Before: Average tokens per Cursor session
   - After: Average tokens per Cursor session
   - Target: 50-70% reduction

2. **Performance:**
   - API response time (should be <10ms overhead)
   - Service latency
   - Error rates

3. **Code Quality:**
   - Lines of code reduction
   - Test coverage
   - Code duplication metrics

## Conclusion

**Recommendation: Implement Option A (PM Service)**

The benefits of reduced context and token usage far outweigh the small overhead of an additional service. The architecture will be cleaner, more maintainable, and more scalable.

**Next Steps:**
1. Review this analysis
2. Get approval for migration
3. Start with Phase 1 (PM Service creation)
4. Iterate and migrate incrementally

