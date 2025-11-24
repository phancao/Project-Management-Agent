# Project Management Agent - Codebase Overview

## 📋 Project Summary

**Project Management Agent** is a sophisticated AI-powered project management system that combines deep research capabilities with intelligent conversation flow management. It integrates DeerFlow (a research framework), OpenAI AgentSDK, and modern web technologies to provide an intelligent assistant for project planning, task management, and team collaboration.

## 🎯 Core Purpose

The system serves as an intelligent project management assistant that can:
- Conduct deep research on topics using DeerFlow
- Create and manage projects with AI-driven planning
- Break down projects into Work Breakdown Structures (WBS)
- Plan and track sprints with burndown charts
- Integrate with multiple PM providers (OpenProject, JIRA, ClickUp)
- Provide conversational interfaces for natural language project management
- Learn and adapt conversation flows based on user interactions

## 🏗️ Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                          │
│  - Chat interface (OpenAI ChatKit)                             │
│  - Project dashboard                                            │
│  - Task management UI                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   API Gateway (FastAPI)                         │
│  - REST APIs                                                    │
│  - WebSocket for real-time updates                             │
│  - Authentication & Authorization                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Conversation Flow Manager                          │
│  - Intent classification                                        │
│  - Context management                                           │
│  - Progressive data gathering                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Agent Orchestration                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  DeerFlow    │  │  AgentSDK    │  │  Custom      │         │
│  │  Research    │  │  Project Mgmt│  │  Agents      │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                Data & Knowledge Layer                           │
│  - PostgreSQL (relational data)                                │
│  - Qdrant (vector store)                                       │
│  - Redis (caching)                                             │
└─────────────────────────────────────────────────────────────────┘
```

### Data Fetching Architecture

The system uses a **hybrid approach** for data fetching:

#### Path 1: Direct REST API (UI Data Fetching)
```
Frontend → Backend REST API → PMHandler → PM Providers → External APIs
```
- **Used for**: Page loads, CRUD operations, real-time UI updates, charts
- **Characteristics**: Fast (~10-50ms), cached, type-safe, simple

#### Path 2: MCP Server (Conversational Queries)
```
Frontend → Backend Chat → DeerFlow Agent → MCP Server → PMHandler → PM Providers
```
- **Used for**: Natural language queries, complex operations, multi-step operations
- **Characteristics**: Intelligent, flexible, composable, slower (~100-500ms)

## 📁 Directory Structure

### Root Level
```
/
├── main.py                  # Main entry point for DeerFlow
├── server.py                # Server entry point for FastAPI
├── pyproject.toml           # Python project configuration
├── docker-compose.yml       # Docker orchestration
├── conf.yaml                # Runtime configuration (not in VCS)
└── .env                     # Environment variables (not in VCS)
```

### Core Directories

#### `/src/` - Main Source Code
The primary application code organized by feature:
- `agents/` - Agent implementations
- `analytics/` - Analytics and metrics
- `config/` - Configuration management
- `conversation/` - Conversation flow management
- `crawler/` - Web crawling utilities
- `graph/` - LangGraph workflow definitions
- `handlers/` - Request handlers
- `llms/` - LLM integrations
- `mcp_servers/` - MCP server implementations
- `pm_providers/` - PM provider integrations
- `prompts/` - LLM prompts
- `rag/` - RAG (Retrieval Augmented Generation)
- `server/` - FastAPI server code
- `tools/` - Agent tools
- `utils/` - Utility functions
- `workflow.py` - Main workflow orchestration

#### `/backend/` - Backend Source (mirrors `/src/`)
Contains the same structure as `/src/` - appears to be a duplicate or symlink structure.

#### `/pm_providers/` - PM Provider Abstraction Layer
Unified interface for different project management systems:
- `base.py` - Base provider interface
- `internal.py` - Internal database provider
- `openproject.py` - OpenProject API integration (v16)
- `openproject_v13.py` - OpenProject v13.4.1 support
- `jira.py` - JIRA integration (stub)
- `clickup.py` - ClickUp integration (stub)
- `factory.py` - Provider factory pattern
- `builder.py` - Provider builder
- `models.py` - Unified data models

#### `/mcp_server/` - MCP Server Implementation
Model Context Protocol server for agent tool access:
- `server.py` - MCP server implementation
- `pm_handler.py` - PM operations handler
- `tools/` - MCP tool definitions
- `services/` - Business logic services
- `auth/` - Authentication & authorization
- `database/` - MCP server database
- `transports/` - Transport implementations (SSE, HTTP, stdio)

#### `/web/` or `/frontend/` - Next.js Frontend
Modern React-based frontend:
- `src/` - Source code
  - `app/` - Next.js app router pages
  - `components/` - React components
  - `hooks/` - Custom React hooks
  - `lib/` - Utility libraries
  - `types/` - TypeScript type definitions
- `public/` - Static assets
- `tests/` - Frontend tests

#### `/database/` - Database Layer
Database schemas and utilities:
- `schema.sql` - Main database schema
- `mcp_server_schema.sql` - MCP server schema
- `sprints_schema.sql` - Sprint management schema
- `intent_learning_schema.sql` - Intent learning schema
- `models.py` - Pydantic models
- `orm_models.py` - SQLAlchemy ORM models
- `crud.py` - CRUD operations
- `connection.py` - Database connection management
- `migrations/` - Alembic migrations

#### `/scripts/` - Utility Scripts
- `utils/` - Utility scripts (provider management, database, setup)
- `fixes/` - Fix/repair scripts
- `dev/` - Development helper scripts
- `tests/` - Standalone test scripts

#### `/tests/` - Official Test Suite
Automated unit and integration tests using pytest.

#### `/docs/` - Documentation
- `guides/` - Comprehensive guides
- `reports/` - Implementation summaries and reports
- Main documentation files

## 🔑 Key Components

### 1. DeerFlow Research Agent
- **Location**: `src/workflow.py`, `src/graph/`
- **Purpose**: Conducts deep research using web search and LLMs
- **Features**:
  - Background investigation
  - Multi-turn clarification
  - Plan-execute-reflect workflow
  - Streaming results

### 2. PM Provider System
- **Location**: `pm_providers/`
- **Purpose**: Unified abstraction for different PM systems
- **Supported Providers**:
  - ✅ Internal (PostgreSQL database)
  - ✅ OpenProject (v13 & v16)
  - 🚧 JIRA (stub)
  - 🚧 ClickUp (stub)

### 3. MCP Server
- **Location**: `mcp_server/`
- **Purpose**: Provides tools for agents via Model Context Protocol
- **Features**:
  - PM operations (projects, tasks, sprints, users)
  - Authentication & RBAC
  - Multiple transports (SSE, HTTP, stdio)
  - Health checks and monitoring

### 4. FastAPI Backend
- **Location**: `src/server/app.py`, `backend/server/app.py`
- **Purpose**: Main API gateway
- **Key Files**:
  - `app.py` - Main FastAPI application (151KB!)
  - `pm_handler.py` - PM operations handler
  - `chat_request.py` - Chat endpoint handlers
  - `mcp_request.py` - MCP integration
  - `rag_request.py` - RAG operations

### 5. Next.js Frontend
- **Location**: `web/` or `frontend/`
- **Purpose**: User interface
- **Features**:
  - Chat interface with OpenAI ChatKit
  - Project dashboard
  - Task management
  - Sprint planning
  - Burndown charts

### 6. Database Layer
- **Location**: `database/`
- **Databases**:
  - **Main DB** (PostgreSQL): Projects, tasks, users, teams
  - **MCP DB** (PostgreSQL): MCP server data, auth, connections
  - **Vector DB** (Qdrant): Embeddings for RAG
  - **Cache** (Redis): Session data, caching

## 🔄 Data Flow

### 1. User Query Flow (Research)
```
User Input → main.py → workflow.py → LangGraph → DeerFlow Agents
  → Web Search → LLM Processing → Research Results → User
```

### 2. PM Operation Flow (Direct API)
```
Frontend → REST API → pm_handler.py → PMProvider → External PM System
  → Response → Frontend Update
```

### 3. PM Operation Flow (Conversational)
```
User Chat → Backend Chat API → DeerFlow Agent → MCP Server
  → PM Tools → PMProvider → External PM System → Response
  → Agent → User
```

## 🛠️ Technology Stack

### Backend
- **Python 3.12+** - Core language
- **FastAPI** - API framework
- **DeerFlow** - Research framework
- **LangChain** - LLM framework
- **LangGraph** - Agent workflows
- **PostgreSQL** - Relational database
- **Qdrant** - Vector database
- **Redis** - Caching
- **SQLAlchemy** - ORM
- **Alembic** - Database migrations
- **Pydantic** - Data validation

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **OpenAI ChatKit** - Chat interface
- **Tailwind CSS** - Styling
- **React Query** - Data fetching
- **Socket.io** - Real-time communication

### AI & ML
- **OpenAI GPT-4o-mini** - Primary LLM
- **OpenAI Embeddings** - Vector embeddings
- **LiteLLM** - Multi-provider LLM support

### DevOps
- **Docker** - Containerization
- **Docker Compose** - Orchestration
- **uv** - Python package manager
- **pytest** - Testing
- **Ruff** - Linting & formatting

## 🚀 Entry Points

### 1. Research Mode (CLI)
```bash
python main.py "What is quantum computing?"
python main.py --interactive
```

### 2. API Server
```bash
python server.py --host localhost --port 8000
uvicorn src.server:app --reload
```

### 3. MCP Server
```bash
python -m mcp_server.server
```

### 4. Docker Compose (Full Stack)
```bash
docker-compose up
```

## 🔐 Configuration

### Environment Variables
Key variables in `.env`:
- `OPENAI_API_KEY` - OpenAI API key
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `PM_PROVIDER` - PM provider selection (internal/openproject/jira/clickup)
- `OPENPROJECT_URL` - OpenProject instance URL
- `OPENPROJECT_API_KEY` - OpenProject API key
- `PM_MCP_SERVER_URL` - MCP server URL
- `PM_MCP_API_KEY` - MCP server authentication

### Configuration Files
- `conf.yaml` - Runtime configuration (LLM settings, search engine)
- `pyproject.toml` - Python project metadata
- `langgraph.json` - LangGraph configuration
- `docker-compose.yml` - Service orchestration

## 📊 Database Schema

### Main Database Tables
- `users` - User accounts
- `projects` - Project information
- `tasks` - Task details
- `team_members` - Team assignments
- `sprints` - Sprint data
- `research_sessions` - Research history
- `knowledge_base` - Vector-stored knowledge
- `conversation_sessions` - Chat sessions
- `project_metrics` - Analytics

### MCP Database Tables
- `users` - MCP server users
- `api_keys` - API key management
- `pm_provider_connections` - External PM connections
- `project_sync_mappings` - Sync mappings

## 🧪 Testing

### Test Organization
- **Official Tests**: `tests/` - Pytest suite
- **Standalone Tests**: `scripts/tests/` - Manual testing scripts

### Running Tests
```bash
# Backend tests
uv run pytest

# Frontend tests
cd frontend && npm test

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 🔍 Key Patterns

### 1. Provider Pattern
The PM provider system uses a factory pattern to abstract different PM systems behind a unified interface.

### 2. Agent Pattern
LangGraph-based agents with tool calling for research and PM operations.

### 3. MCP Protocol
Model Context Protocol for exposing tools to agents in a standardized way.

### 4. Hybrid Data Fetching
Direct REST APIs for UI, MCP for conversational queries.

### 5. Progressive Data Gathering
Conversation flows that incrementally collect required information.

## 📝 Important Files to Review

### Core Logic
1. `src/workflow.py` - Main workflow orchestration
2. `src/server/app.py` - FastAPI application (151KB - very large!)
3. `pm_providers/base.py` - PM provider interface
4. `mcp_server/server.py` - MCP server implementation

### Configuration
5. `pyproject.toml` - Dependencies and project config
6. `docker-compose.yml` - Service orchestration
7. `database/schema.sql` - Database schema

### Documentation
8. `README.md` - Main documentation
9. `pm_providers/README.md` - PM provider docs
10. `mcp_server/README.md` - MCP server docs

## 🎓 Learning Path

### For New Developers
1. **Start with README.md** - Understand the project vision
2. **Review docker-compose.yml** - See how services connect
3. **Explore database/schema.sql** - Understand data model
4. **Read pm_providers/README.md** - Learn provider abstraction
5. **Study src/workflow.py** - Understand agent workflow
6. **Examine src/server/app.py** - See API endpoints
7. **Review frontend structure** - Understand UI organization

### For AI/ML Focus
1. Study `src/graph/` - LangGraph workflows
2. Review `src/agents/` - Agent implementations
3. Explore `src/prompts/` - LLM prompts
4. Check `src/rag/` - RAG implementation

### For Backend Focus
1. Study `src/server/app.py` - API endpoints
2. Review `pm_providers/` - Provider implementations
3. Explore `database/` - Data layer
4. Check `mcp_server/` - MCP protocol

### For Frontend Focus
1. Study `web/src/app/` - Next.js pages
2. Review `web/src/components/` - React components
3. Explore `web/src/hooks/` - Custom hooks
4. Check `web/src/lib/` - Utility libraries

## 🚧 Current Status

### ✅ Completed
- DeerFlow research integration
- Internal PM provider
- OpenProject integration (v13 & v16)
- MCP server implementation
- FastAPI backend
- Next.js frontend
- Docker orchestration
- Authentication & RBAC

### 🚧 In Progress
- JIRA integration (stub created)
- ClickUp integration (stub created)
- Advanced analytics
- Enhanced conversation flows

### 📋 Planned
- Asana integration
- Trello integration
- Webhook support
- Real-time collaboration features
- Mobile app

## 💡 Key Insights

1. **Dual Architecture**: The system cleverly uses both direct REST APIs (for speed) and MCP/agents (for intelligence)

2. **Provider Abstraction**: The PM provider pattern allows easy switching between different PM systems

3. **Research-Driven**: DeerFlow integration enables deep research capabilities beyond typical PM tools

4. **Conversation-First**: The system is designed for natural language interaction, not just UI clicks

5. **Modular Design**: Clear separation between research, PM operations, and UI layers

6. **Docker-First**: Everything is containerized for easy deployment

7. **Type Safety**: Heavy use of Pydantic and TypeScript for data validation

8. **Extensible**: Easy to add new PM providers, agents, or tools

## 🔗 External Integrations

- **OpenAI** - LLM and embeddings
- **OpenProject** - PM system (v13 & v16)
- **DuckDuckGo** - Web search
- **PostgreSQL** - Database
- **Redis** - Caching
- **Qdrant** - Vector store

## 📚 Additional Resources

- Main README: [README.md](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/README.md)
- PM Providers: [pm_providers/README.md](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/pm_providers/README.md)
- Project Structure: [.project-structure.md](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/.project-structure.md)
- Contributing: [CONTRIBUTING](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/CONTRIBUTING)

---

**Last Updated**: 2025-11-22
**Codebase Version**: Based on current repository state
