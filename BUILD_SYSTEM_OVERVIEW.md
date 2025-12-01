# Build System & Codebase Overview

## 🏗️ Architecture Overview

The Project Management Agent is a **three-tier microservices architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                       │
│  - Next.js 15.5.6 with Turbopack                           │
│  - TypeScript + React                                        │
│  - Port: 3000                                                │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/WebSocket
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend API (FastAPI + LangGraph)              │
│  - FastAPI server                                            │
│  - LangGraph agent orchestration                             │
│  - Port: 8000                                                │
└──────────────┬───────────────────────┬──────────────────────┘
               │                       │
               │ MCP Protocol          │ HTTP REST
               │ (SSE/HTTP)            │
               ▼                       ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│   PM MCP Server          │  │   PM Service                  │
│   (MCP Protocol)         │  │   (REST API)                  │
│   - Port: 8080           │  │   - Port: 8001                │
│   - Tools for AI agents  │  │   - PM provider abstraction  │
└──────────┬───────────────┘  └──────────────┬───────────────┘
           │                                  │
           └──────────────┬───────────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │   PM Providers               │
           │   - OpenProject              │
           │   - JIRA                    │
           │   - ClickUp                 │
           │   - Internal DB             │
           └──────────────────────────────┘
```

---

## 📦 Component Breakdown

### 1. **Frontend + Backend** (Monorepo)

**Location:** `./web/` (frontend) + `./src/` (backend)

#### Frontend (`web/`)
- **Framework:** Next.js 15.5.6 with Turbopack
- **Language:** TypeScript
- **Package Manager:** pnpm
- **Entry Point:** `web/src/app/`
- **Build Command:** `pnpm run build`
- **Dev Command:** `pnpm run dev` (uses `dotenv -f ../.env -- next dev --turbo`)
- **Dockerfile:** `web/Dockerfile.dev` (development) + `web/Dockerfile` (production)

**Key Dependencies:**
- Next.js 15.5.6
- React 18+
- TypeScript
- Tailwind CSS
- Radix UI components
- TanStack Query (React Query)
- Zustand (state management)

#### Backend (`src/`)
- **Framework:** FastAPI
- **Language:** Python 3.12
- **Package Manager:** uv (via `pyproject.toml`)
- **Entry Point:** `src/server/app.py` → `backend.server.app:app`
- **Run Command:** `uv run uvicorn backend.server.app:app --host 0.0.0.0 --port 8000`
- **Dockerfile:** `Dockerfile.api`

**Key Dependencies (from `pyproject.toml`):**
- FastAPI >= 0.110.0
- LangGraph >= 0.3.5
- LangChain >= 0.3.19
- Uvicorn >= 0.27.1
- PostgreSQL (psycopg[binary] >= 3.2.9)
- Redis >= 7.0.1

**Key Directories:**
- `src/graph/` - LangGraph workflow definitions
- `src/server/` - FastAPI routes and handlers
- `src/agents/` - Agent implementations
- `src/prompts/` - LLM prompts
- `src/config/` - Configuration management

---

### 2. **PM MCP Server** (Standalone Service)

**Location:** `./mcp_server/`

- **Purpose:** Exposes PM operations as MCP (Model Context Protocol) tools for AI agents
- **Framework:** FastAPI (SSE/HTTP transports) + MCP SDK
- **Language:** Python 3.12
- **Package Manager:** uv (via root `pyproject.toml`)
- **Entry Point:** `scripts/run_pm_mcp_server.py`
- **Run Command:** 
  - SSE: `uv run python scripts/run_pm_mcp_server.py --transport sse --host 0.0.0.0 --port 8080`
  - HTTP: `uv run python scripts/run_pm_mcp_server.py --transport http --host 0.0.0.0 --port 8080`
  - stdio: `uv run python scripts/run_pm_mcp_server.py --transport stdio`
- **Dockerfile:** `Dockerfile.mcp-server`
- **Port:** 8080

**Key Features:**
- 50+ PM tools (projects, tasks, sprints, epics, users, analytics)
- Multiple transports: stdio (Claude Desktop), SSE (web agents), HTTP (REST API)
- Authentication & authorization
- Database: Separate PostgreSQL instance (`mcp_postgres` on port 5435)

**Key Files:**
- `mcp_server/server.py` - Main server class (`PMMCPServer`)
- `mcp_server/tools/` - Tool implementations
- `mcp_server/transports/` - Transport implementations (SSE, HTTP, stdio)
- `mcp_server/database/` - Database models and connection

---

### 3. **PM Service** (Microservice)

**Location:** `./pm_service/`

- **Purpose:** Unified REST API for PM provider interactions (abstraction layer)
- **Framework:** FastAPI
- **Language:** Python 3.12
- **Package Manager:** pip (via `requirements.txt`)
- **Entry Point:** `pm_service/main.py`
- **Run Command:** `uvicorn pm_service.main:app --host 0.0.0.0 --port 8001`
- **Dockerfile:** `pm_service/Dockerfile`
- **Port:** 8001

**Key Dependencies (from `pm_service/requirements.txt`):**
- FastAPI >= 0.104.0
- Uvicorn >= 0.24.0
- Pydantic >= 2.0.0
- SQLAlchemy >= 2.0.0
- PostgreSQL (psycopg2-binary >= 2.9.0)
- httpx >= 0.25.0

**Key Directories:**
- `pm_service/routers/` - FastAPI route handlers
- `pm_service/providers/` - PM provider implementations
- `pm_service/handlers/` - Business logic handlers
- `pm_service/models/` - Data models
- `pm_service/database/` - Database connection

**Consumers:**
- Backend API (for web UI data fetching)
- MCP Server (for AI agent tool calls)

---

## 🐳 Docker Compose Architecture

**File:** `docker-compose.yml`

### Services:

1. **postgres** (Main Database)
   - Image: `pgvector/pgvector:pg15`
   - Port: 5432
   - Database: `project_management`
   - Used by: Backend API

2. **mcp_postgres** (MCP Server Database)
   - Image: `pgvector/pgvector:pg15`
   - Port: 5435
   - Database: `mcp_server`
   - Used by: PM MCP Server, PM Service

3. **redis** (Cache)
   - Image: `redis:7-alpine`
   - Port: 6379
   - Used by: Backend API

4. **api** (Backend API)
   - Build: `Dockerfile.api`
   - Port: 8000
   - Depends on: postgres, redis, pm_mcp_server, pm_service

5. **frontend** (Next.js Frontend)
   - Build: `web/Dockerfile.dev`
   - Port: 3000
   - Depends on: api

6. **pm_mcp_server** (PM MCP Server)
   - Build: `Dockerfile.mcp-server`
   - Port: 8080
   - Depends on: mcp_postgres, pm_service

7. **pm_service** (PM Service)
   - Build: `pm_service/Dockerfile`
   - Port: 8001
   - Depends on: mcp_postgres

8. **openproject_v13** (OpenProject Instance)
   - Image: `openproject/openproject:13.4.1`
   - Port: 8083
   - For testing/development

---

## 🔧 Build Commands

### Local Development

#### Backend API
```bash
# Install dependencies
uv sync

# Run development server
uv run uvicorn backend.server.app:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend
```bash
cd web
pnpm install
pnpm run dev  # Uses dotenv -f ../.env -- next dev --turbo
```

#### PM MCP Server
```bash
# SSE transport (for web agents)
uv run python scripts/run_pm_mcp_server.py --transport sse --host 0.0.0.0 --port 8080

# HTTP transport (REST API)
uv run python scripts/run_pm_mcp_server.py --transport http --host 0.0.0.0 --port 8080

# stdio transport (for Claude Desktop)
uv run python scripts/run_pm_mcp_server.py --transport stdio
```

#### PM Service
```bash
cd pm_service
pip install -r requirements.txt
uvicorn pm_service.main:app --host 0.0.0.0 --port 8001 --reload
```

### Docker Development

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d api frontend pm_mcp_server pm_service

# View logs
docker-compose logs -f api
docker-compose logs -f pm_mcp_server
docker-compose logs -f pm_service

# Rebuild specific service
docker-compose build api
docker-compose up -d api
```

### Production Build

```bash
# Build all images
docker-compose build

# Or build specific service
docker-compose build api
docker-compose build pm_mcp_server
docker-compose build pm_service
docker-compose build frontend
```

---

## 📁 Directory Structure

```
Project-Management-Agent/
├── web/                    # Next.js frontend
│   ├── src/
│   │   ├── app/           # Next.js app router
│   │   ├── core/          # Core utilities (store, API, etc.)
│   │   └── ...
│   ├── package.json
│   ├── Dockerfile.dev
│   └── Dockerfile
│
├── src/                    # Backend API (FastAPI + LangGraph)
│   ├── server/            # FastAPI app and routes
│   ├── graph/             # LangGraph workflows
│   ├── agents/            # Agent implementations
│   ├── prompts/           # LLM prompts
│   ├── config/            # Configuration
│   └── ...
│
├── mcp_server/             # PM MCP Server (standalone)
│   ├── server.py          # Main server class
│   ├── tools/             # MCP tool implementations
│   ├── transports/        # Transport implementations (SSE, HTTP, stdio)
│   ├── database/          # Database models
│   └── ...
│
├── pm_service/             # PM Service (microservice)
│   ├── main.py            # FastAPI app entry point
│   ├── routers/           # API routes
│   ├── providers/         # PM provider implementations
│   ├── handlers/          # Business logic
│   ├── models/            # Data models
│   ├── requirements.txt
│   └── Dockerfile
│
├── pm_providers/           # Shared PM provider code
├── shared/                 # Shared utilities
├── database/               # Database schemas and migrations
├── scripts/                # Utility scripts
├── tests/                  # Tests
│
├── pyproject.toml          # Python dependencies (root)
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile.api          # Backend API Dockerfile
├── Dockerfile.mcp-server   # MCP Server Dockerfile
└── README.md
```

---

## 🔄 Data Flow

### 1. **Web UI Data Fetching** (Direct REST API)
```
Frontend → Backend API → PM Service → PM Providers → External APIs
```
- Fast: ~10-50ms latency
- Cached: React Query caching
- Type-safe: TypeScript ↔ FastAPI with Pydantic

### 2. **AI Agent Tool Calls** (MCP Protocol)
```
Backend API → PM MCP Server → PM Service → PM Providers → External APIs
```
- Uses MCP (Model Context Protocol)
- SSE transport for web agents
- stdio transport for Claude Desktop
- HTTP transport for REST API access

### 3. **PM Service Abstraction**
```
PM Service → Provider Factory → OpenProject/JIRA/ClickUp/Internal DB
```
- Unified interface for all PM providers
- Handles authentication, rate limiting, error handling
- Database-backed credential storage

---

## 🔐 Authentication & Security

### Backend API → PM MCP Server
- **API Key:** `PM_MCP_API_KEY` environment variable
- Default: `mcp_a9b43d595b627e1e094209dea14bcb32f98867649ae181d4836dde87e283ccc3`
- Used to authenticate backend service to MCP server

### PM MCP Server
- **Authentication:** Token-based (optional, via `ENABLE_AUTH`)
- **RBAC:** Role-based access control (optional, via `ENABLE_RBAC`)
- **User Context:** User-scoped credential loading

### PM Service
- **Database:** Uses MCP Server database for credential storage
- **Provider Auth:** Handles provider-specific authentication (API keys, tokens)

---

## 🧪 Testing

### Backend API
```bash
# Run tests
pytest

# With coverage
pytest --cov=backend --cov=mcp_server --cov=pm_providers --cov=pm_service
```

### PM MCP Server
```bash
# Test MCP server
python scripts/test_pm_mcp_sse.py
python scripts/test_pm_mcp_integration.py
```

### PM Service
```bash
cd pm_service
pytest
```

---

## 📝 Environment Variables

### Backend API (`.env`)
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `OPENAI_API_KEY` - OpenAI API key
- `PM_MCP_SERVER_URL` - MCP server URL (default: `http://pm_mcp_server:8080/sse`)
- `PM_MCP_TRANSPORT` - Transport type (sse/http/stdio)
- `PM_MCP_API_KEY` - API key for MCP server authentication
- `PM_SERVICE_URL` - PM Service URL (default: `http://pm-service:8001`)

### PM MCP Server
- `DATABASE_URL` - MCP server database connection
- `MCP_TRANSPORT` - Transport type (sse/http/stdio)
- `MCP_HOST` - Host (default: `0.0.0.0`)
- `MCP_PORT` - Port (default: `8080`)
- `ENABLE_AUTH` - Enable authentication (default: `false`)
- `ENABLE_RBAC` - Enable RBAC (default: `false`)

### PM Service
- `PM_SERVICE_DATABASE_URL` - Database connection
- `PM_SERVICE_OPENPROJECT_URL` - OpenProject URL
- `PM_SERVICE_LOG_LEVEL` - Log level (default: `INFO`)

---

## 🚀 Quick Start

1. **Clone and setup:**
   ```bash
   git clone <repo>
   cd Project-Management-Agent
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Start with Docker:**
   ```bash
   docker-compose up -d
   ```

3. **Or run locally:**
   ```bash
   # Terminal 1: Backend API
   uv sync
   uv run uvicorn backend.server.app:app --host 0.0.0.0 --port 8000 --reload

   # Terminal 2: PM MCP Server
   uv run python scripts/run_pm_mcp_server.py --transport sse --host 0.0.0.0 --port 8080

   # Terminal 3: PM Service
   cd pm_service
   pip install -r requirements.txt
   uvicorn pm_service.main:app --host 0.0.0.0 --port 8001 --reload

   # Terminal 4: Frontend
   cd web
   pnpm install
   pnpm run dev
   ```

4. **Access:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - PM MCP Server: http://localhost:8080
   - PM Service: http://localhost:8001
   - API Docs: http://localhost:8000/docs

---

## 📚 Key Technologies

- **Frontend:** Next.js 15, React, TypeScript, Tailwind CSS
- **Backend:** FastAPI, Python 3.12, LangGraph, LangChain
- **MCP Server:** MCP SDK, FastAPI, SSE/HTTP/stdio transports
- **PM Service:** FastAPI, SQLAlchemy, Pydantic
- **Database:** PostgreSQL (with pgvector), Redis
- **Package Managers:** pnpm (frontend), uv (Python backend)
- **Containerization:** Docker, Docker Compose

---

## 🔍 Debugging

### Check service health:
```bash
curl http://localhost:8000/health  # Backend API
curl http://localhost:8080/health # PM MCP Server
curl http://localhost:8001/health # PM Service
```

### View logs:
```bash
# Docker
docker-compose logs -f api
docker-compose logs -f pm_mcp_server
docker-compose logs -f pm_service

# Local
# Check console output for each service
```

### Database connections:
```bash
# Main database (Backend API)
psql postgresql://pm_user:pm_password@localhost:5432/project_management

# MCP database (MCP Server + PM Service)
psql postgresql://mcp_user:mcp_password@localhost:5435/mcp_server
```

---

## 📖 Additional Resources

- `README.md` - Main project documentation
- `CODEBASE_LEARNING_SUMMARY.md` - Detailed codebase walkthrough
- `ARCHITECTURE_REVIEW.md` - Architecture deep dive
- `mcp_server/README.md` - MCP Server documentation
- `pm_service/README.md` - PM Service documentation

