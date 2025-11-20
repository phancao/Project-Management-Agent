# Project Restructuring Plan

## Current Structure
```
src/
├── mcp_servers/pm_server/    # MCP server code
├── pm_providers/             # PM provider implementations
├── server/                   # FastAPI backend server
├── agents/                   # Agent implementations
├── analytics/                # Analytics calculations
├── conversation/             # Conversation flow management
├── graph/                    # LangGraph implementations
├── handlers/                 # Request handlers
├── llms/                     # LLM providers
├── prompts/                  # Prompt templates
├── rag/                      # RAG implementations
├── tools/                    # Tool implementations
└── utils/                    # Utility functions
```

## New Structure
```
backend/                      # Main application server
├── agents/
├── analytics/
├── conversation/
├── graph/
├── handlers/
├── llms/
├── prompts/
├── rag/
├── server/                   # FastAPI server
├── tools/
└── utils/

mcp-server/                   # MCP server (separate service)
├── server.py
├── pm_handler.py
├── config.py
├── auth/
├── tools/
└── transports/

pm-providers/                # PM provider implementations (shared)
├── __init__.py
├── base.py
├── builder.py
├── factory.py
├── models.py
├── internal.py
├── openproject.py
├── openproject_v13.py
├── jira.py
├── clickup.py
└── mock_provider.py

shared/                      # Shared code between backend and mcp-server
├── database/                # Database models and connection
│   ├── __init__.py
│   ├── connection.py
│   ├── crud.py
│   └── orm_models.py
├── config/                  # Shared configuration
│   ├── __init__.py
│   └── configuration.py
└── models/                  # Shared data models (if any)

database/                    # Database schemas and migrations (keep as is)
├── schema.sql
├── mcp_server_schema.sql
└── migrations/

scripts/                     # Utility scripts (keep as is)
tests/                       # Tests (keep as is)
web/                         # Web frontend (keep as is)
frontend/                    # Frontend (keep as is)
```

## Migration Steps

1. **Create new directories**
2. **Move MCP server code** from `mcp_server/` to `mcp-server/`
3. **Move PM providers** from `pm_providers/` to `pm-providers/`
4. **Move backend code** from `backend/` (excluding mcp_servers and pm_providers) to `backend/`
5. **Move shared code** (database, config) to `shared/`
6. **Update imports** across all files
7. **Update Dockerfiles** and docker-compose.yml
8. **Update pyproject.toml** if needed
9. **Update test imports**

## Import Path Changes

### Before → After
- `backend.mcp_servers.pm_server.*` → `mcp_server.*`
- `backend.pm_providers.*` → `pm_providers.*`
- `backend.server.*` → `backend.server.*`
- `backend.agents.*` → `backend.agents.*`
- `backend.analytics.*` → `backend.analytics.*`
- `backend.conversation.*` → `backend.conversation.*`
- `backend.graph.*` → `backend.graph.*`
- `backend.handlers.*` → `backend.handlers.*`
- `backend.llms.*` → `backend.llms.*`
- `backend.prompts.*` → `backend.prompts.*`
- `backend.rag.*` → `backend.rag.*`
- `backend.tools.*` → `backend.tools.*`
- `backend.utils.*` → `backend.utils.*`
- `database.*` → `shared.database.*` (or keep as `database.*` if preferred)

