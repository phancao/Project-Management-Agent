# Architecture Review: MCP Server & Backend Separation

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    FRONTEND                                          │
│                                  (Next.js)                                           │
│                                                                                      │
│  ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────────┐  │
│  │  Provider Manager   │    │   Project Selector  │    │    Chat Interface       │  │
│  │  (Configure PM)     │    │   (List Projects)   │    │    (AI Agent)           │  │
│  └──────────┬──────────┘    └──────────┬──────────┘    └───────────┬─────────────┘  │
│             │                          │                           │                 │
└─────────────┼──────────────────────────┼───────────────────────────┼─────────────────┘
              │                          │                           │
              │ /api/pm/providers        │ /api/pm/projects          │ /api/pm/chat/stream
              │ /api/pm/providers/import │ /api/pm/.../sprints       │ (includes mcp_settings)
              ▼                          ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    BACKEND API                                       │
│                                   (FastAPI)                                          │
│                                                                                      │
│  ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────────┐  │
│  │  Provider Endpoints │    │   PM Data Endpoints │    │   AI Workflow Engine    │  │
│  │  - list_providers   │    │   - list_projects   │    │   - LangGraph           │  │
│  │  - import_projects  │    │   - list_sprints    │    │   - Planner/PM Agent    │  │
│  │  - update_provider  │    │   - list_tasks      │    │   - Reporter            │  │
│  └──────────┬──────────┘    └──────────┬──────────┘    └───────────┬─────────────┘  │
│             │                          │                           │                 │
│             ▼                          ▼                           │                 │
│  ┌─────────────────────────────────────────────────┐               │                 │
│  │              Backend PMHandler                   │               │                 │
│  │  - Uses Backend Database providers               │               │                 │
│  │  - Creates PM Provider instances                 │               │                 │
│  └──────────────────────┬──────────────────────────┘               │                 │
│                         │                                          │                 │
└─────────────────────────┼──────────────────────────────────────────┼─────────────────┘
                          │                                          │
                          ▼                                          │ MCP Protocol
┌─────────────────────────────────────┐                              │ (SSE Transport)
│        BACKEND DATABASE             │                              │
│        (PostgreSQL)                 │                              │
│        Port: 5432                   │                              │
│                                     │                              │
│  ┌─────────────────────────────┐    │                              │
│  │  pm_provider_connections    │    │                              │
│  │  - id: d7e300c6-...         │    │                              │
│  │  - api_key: a503...         │    │                              │
│  │  - is_active: true          │    │                              │
│  └─────────────────────────────┘    │                              │
└─────────────────────────────────────┘                              │
                                                                     │
                                                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                  MCP SERVER                                          │
│                                  (FastMCP)                                           │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                           MCP Tools                                          │    │
│  │  - list_providers       - list_projects      - list_sprints                  │    │
│  │  - configure_provider   - get_project        - get_sprint                    │    │
│  │  - list_tasks           - burndown_chart     - velocity_chart                │    │
│  └──────────────────────────────────┬──────────────────────────────────────────┘    │
│                                     │                                               │
│                                     ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                        MCP PMHandler                                         │    │
│  │  - Uses MCP Server Database providers                                        │    │
│  │  - Creates PM Provider instances                                             │    │
│  │  - INDEPENDENT from Backend PMHandler                                        │    │
│  └──────────────────────────────────┬──────────────────────────────────────────┘    │
│                                     │                                               │
└─────────────────────────────────────┼───────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────┐
│           MCP SERVER DATABASE                   │
│           (PostgreSQL)                          │
│           Port: 5435                            │
│                                                 │
│  ┌─────────────────────────────────────────┐    │
│  │  pm_provider_connections                │    │
│  │  - id: 8eedf4f4-...  (DIFFERENT!)       │    │
│  │  - api_key: ???      (MAY BE OUTDATED!) │    │
│  │  - is_active: true                      │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘

                          │
                          │ Both use same PM Provider implementations
                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              PM PROVIDERS (Shared)                                   │
│                                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ OpenProject v13 │  │ OpenProject v16 │  │      JIRA       │  │    ClickUp      │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
│           │                    │                    │                    │          │
└───────────┼────────────────────┼────────────────────┼────────────────────┼──────────┘
            │                    │                    │                    │
            ▼                    ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL PM SYSTEMS                                           │
│                                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ OpenProject v13 │  │ OpenProject v16 │  │  Atlassian JIRA │  │    ClickUp      │ │
│  │ (Port 8083)     │  │ (Port 8082)     │  │  (Cloud)        │  │    (Cloud)      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Current Problems

### 1. **Provider ID Mismatch**
- Backend Database has provider ID: `d7e300c6-d6c0-4c08-bc8d-e41967458d86`
- MCP Server Database has provider ID: `8eedf4f4-6c0e-4061-bca2-4dc10a118f7a`
- Frontend sends Backend's provider ID → MCP Server can't find it

### 2. **API Key Synchronization**
- Backend and MCP Server have SEPARATE copies of API keys
- When API key is updated in Backend, MCP Server's copy becomes outdated
- This caused 401 Unauthorized errors we just fixed manually

### 3. **No Provider Sync Mechanism**
- There's NO automatic sync between Backend and MCP Server providers
- Each service manages its own provider configurations independently
- Changes in one don't reflect in the other

### 4. **Duplicate Configuration Work**
- Users must configure providers in BOTH systems
- Or rely on the `configure_pm_provider` MCP tool (but this creates new entries)

---

## Recommended Architecture Improvements

### Option A: Shared Configuration Source (Environment Variables)

```
┌─────────────────────────────────────────────────────────────────┐
│                    SHARED CONFIGURATION                          │
│                    (.env / Secrets Manager)                      │
│                                                                  │
│  OPENPROJECT_URL=http://host.docker.internal:8083                │
│  OPENPROJECT_API_KEY=a50304d97929f687895df28ac893c24a788140...  │
│  JIRA_URL=https://company.atlassian.net                          │
│  JIRA_API_TOKEN=...                                              │
└──────────────────────────┬───────────────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│   BACKEND API       │         │   MCP SERVER        │
│   Reads from .env   │         │   Reads from .env   │
│   at startup        │         │   at startup        │
└─────────────────────┘         └─────────────────────┘
```

**Pros:**
- Simple, single source of truth
- No sync needed
- Easy to update (just restart services)

**Cons:**
- Requires service restart for changes
- Not suitable for multi-tenant scenarios
- Limited to static configuration

### Option B: Backend as Provider Authority (Recommended)

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│  1. Configure provider via Backend API                           │
│  2. Backend saves to its DB                                      │
│  3. Backend syncs to MCP Server via API                          │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       BACKEND API                                │
│                                                                  │
│  POST /api/pm/providers/import                                   │
│  ├── 1. Save provider to Backend DB                              │
│  ├── 2. Call MCP Server API to sync provider                     │
│  │      POST http://pm_mcp_server:8080/providers/sync            │
│  │      { provider_type, base_url, api_key, ... }                │
│  └── 3. Return success to frontend                               │
│                                                                  │
│  Backend DB: pm_provider_connections                             │
│  - id: d7e300c6-...                                              │
│  - api_key: a503...                                              │
│  - mcp_provider_id: 8eedf4f4-... (NEW: linked MCP provider)      │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           │ Sync API Call
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       MCP SERVER                                 │
│                                                                  │
│  POST /providers/sync (NEW ENDPOINT)                             │
│  ├── 1. Find existing provider by (base_url, provider_type)      │
│  ├── 2. If exists: Update api_key, return existing ID            │
│  └── 3. If not: Create new provider, return new ID               │
│                                                                  │
│  MCP DB: pm_provider_connections                                 │
│  - id: 8eedf4f4-...                                              │
│  - api_key: a503... (SYNCED!)                                    │
│  - backend_provider_id: d7e300c6-... (NEW: linked Backend ID)    │
└─────────────────────────────────────────────────────────────────┘
```

**Pros:**
- Single point of configuration (Backend)
- Automatic sync when providers change
- Supports dynamic updates without restart
- Provider ID mapping maintained

**Cons:**
- Requires new sync API in MCP Server
- Adds complexity to provider management
- Backend must handle sync failures gracefully

### Option C: MCP Server as Provider Authority

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│  1. Configure provider via MCP Server API                        │
│  2. MCP Server saves to its DB                                   │
│  3. Backend queries MCP Server for provider info                 │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       MCP SERVER                                 │
│                                                                  │
│  POST /providers/configure                                       │
│  - Save provider to MCP DB                                       │
│  - Return provider_id                                            │
│                                                                  │
│  GET /providers/{id}                                             │
│  - Return provider config (without sensitive keys)               │
│                                                                  │
│  MCP DB: pm_provider_connections (SINGLE SOURCE OF TRUTH)        │
│  - id: 8eedf4f4-...                                              │
│  - api_key: a503...                                              │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           │ Query API
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       BACKEND API                                │
│                                                                  │
│  - No provider storage                                           │
│  - Queries MCP Server for provider list                          │
│  - Uses MCP Server's provider_id in all operations               │
│                                                                  │
│  Backend DB: NO pm_provider_connections table                    │
└─────────────────────────────────────────────────────────────────┘
```

**Pros:**
- True single source of truth
- No sync needed
- MCP Server owns all PM credentials

**Cons:**
- Major refactoring of Backend
- Backend becomes dependent on MCP Server
- May not align with "independent services" goal

---

## Recommended Implementation: Option B

### Step 1: Add Provider Sync Endpoint to MCP Server

```python
# mcp_server/transports/sse.py or new file: mcp_server/api/providers.py

@app.post("/providers/sync")
async def sync_provider(request: ProviderSyncRequest):
    """
    Sync a provider from Backend to MCP Server.
    
    - If provider with same (base_url, provider_type) exists: Update it
    - If not: Create new provider
    - Return MCP provider_id for Backend to store
    """
    db = get_mcp_db_session()
    
    # Find existing by base_url + provider_type
    existing = db.query(PMProviderConnection).filter(
        PMProviderConnection.base_url == request.base_url,
        PMProviderConnection.provider_type == request.provider_type
    ).first()
    
    if existing:
        # Update existing
        existing.api_key = request.api_key
        existing.api_token = request.api_token
        existing.is_active = True
        db.commit()
        return {"mcp_provider_id": str(existing.id), "action": "updated"}
    else:
        # Create new
        new_provider = PMProviderConnection(
            name=request.name,
            provider_type=request.provider_type,
            base_url=request.base_url,
            api_key=request.api_key,
            api_token=request.api_token,
            is_active=True
        )
        db.add(new_provider)
        db.commit()
        return {"mcp_provider_id": str(new_provider.id), "action": "created"}
```

### Step 2: Update Backend to Sync on Provider Changes

```python
# src/server/app.py

@app.post("/api/pm/providers/import-projects")
async def pm_import_projects(request: ProjectImportRequest):
    # ... existing code to save provider to Backend DB ...
    
    # NEW: Sync to MCP Server
    try:
        mcp_response = await sync_provider_to_mcp(
            base_url=request.base_url,
            provider_type=request.provider_type,
            api_key=request.api_key,
            api_token=request.api_token,
            name=f"{request.provider_type}_{request.base_url}"
        )
        
        # Store MCP provider_id mapping
        backend_provider.mcp_provider_id = mcp_response["mcp_provider_id"]
        db.commit()
        
        logger.info(f"Provider synced to MCP: {mcp_response}")
    except Exception as e:
        logger.warning(f"Failed to sync provider to MCP: {e}")
        # Continue - provider still works for Backend, just not for AI Agent
```

### Step 3: Add Provider ID Mapping to Backend DB

```sql
-- database/schema.sql (add column)
ALTER TABLE pm_provider_connections 
ADD COLUMN mcp_provider_id UUID;
```

### Step 4: Frontend Uses Consistent Provider IDs

When sending `project_id` to the AI Agent:
- Use `mcp_provider_id:project_key` instead of `backend_provider_id:project_key`
- This ensures the MCP Server can find the correct provider

---

## Implemented Solution (Option B)

The sync mechanism has been implemented with the following components:

### MCP Server API Endpoints

```
POST /providers/sync          - Sync a single provider from Backend
POST /providers/sync/bulk     - Sync multiple providers at once
DELETE /providers/sync        - Delete/deactivate a provider
GET /providers/sync/status    - Get sync status of all providers
POST /providers/sync/test/{id} - Test connection for a provider
```

### Backend API Endpoints

```
POST /api/pm/providers/{id}/sync    - Manually sync a provider to MCP
POST /api/pm/providers/sync-all     - Sync all active providers
POST /api/pm/providers/check-sync   - Check and re-sync unhealthy providers
GET /api/pm/providers/sync-status   - Get sync status comparison
```

### Automatic Sync Triggers

1. **On Provider Create** (`/api/pm/providers/import-projects`):
   - Creates provider in Backend DB
   - Syncs to MCP Server via HTTP API
   - Stores `mcp_provider_id` in Backend's `additional_config`

2. **On Provider Update** (`/api/pm/providers/{id}`):
   - Updates provider in Backend DB
   - Re-syncs to MCP Server (critical for API key changes!)
   - Updates `mcp_provider_id` mapping

3. **On Provider Delete** (`/api/pm/providers/{id}`):
   - Deactivates provider in Backend DB
   - Deactivates in MCP Server

4. **On Backend Startup**:
   - Background task syncs all providers to MCP Server
   - Handles MCP Server restarts gracefully

### Provider ID Mapping

The mapping is stored in both databases:

**Backend DB** (`pm_provider_connections.additional_config`):
```json
{
  "mcp_provider_id": "8eedf4f4-6c0e-4061-bca2-4dc10a118f7a"
}
```

**MCP Server DB** (`pm_provider_connections.additional_config`):
```json
{
  "backend_provider_id": "d7e300c6-d6c0-4c08-bc8d-e41967458d86"
}
```

### Fallback Logic

When MCP Server receives a project_id with a provider_id that doesn't match:
1. First tries to match by `backend_provider_id` in `additional_config`
2. Then tries to match by `base_url + provider_type`
3. Finally searches all providers by project_key

---

## Summary

| Aspect | Previous State | Current State |
|--------|---------------|---------------|
| Databases | Separate ✓ | Separate ✓ |
| Provider Config | Duplicated, unsynchronized ✗ | Auto-synced via HTTP API ✓ |
| API Keys | Manually copied, can drift ✗ | Auto-sync on change ✓ |
| Provider IDs | Different UUIDs, no mapping ✗ | Bidirectional mapping ✓ |
| Token Expiration | Manual detection ✗ | Health check endpoint ✓ |
| Startup Sync | None ✗ | Background task ✓ |

