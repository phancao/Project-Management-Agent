# Test Restructuring Plan

## Current Structure
```
tests/
├── unit/
│   ├── server/          # Backend server tests
│   ├── agents/          # Backend agents tests
│   ├── graph/           # Backend graph tests
│   ├── tools/           # Backend tools tests
│   ├── config/          # Backend config tests
│   └── ...
├── integration/
└── test_*.py            # Root level tests
```

## Proposed Structure
```
tests/
├── backend/             # Backend service tests
│   ├── unit/
│   │   ├── server/      # FastAPI server tests
│   │   ├── agents/      # Agent tests
│   │   ├── graph/       # LangGraph tests
│   │   ├── tools/       # Tool tests
│   │   ├── analytics/   # Analytics tests
│   │   ├── conversation/# Conversation flow tests
│   │   ├── handlers/    # Handler tests
│   │   ├── llms/        # LLM tests
│   │   ├── prompts/     # Prompt tests
│   │   ├── rag/         # RAG tests
│   │   ├── crawler/     # Crawler tests
│   │   ├── config/      # Config tests
│   │   └── utils/       # Utils tests
│   └── integration/     # Backend integration tests
│
├── mcp_server/          # MCP server tests
│   ├── unit/
│   │   ├── server/      # Server tests
│   │   ├── tools/       # Tool registration tests
│   │   ├── transports/  # Transport tests (SSE, HTTP)
│   │   ├── auth/        # Auth tests
│   │   └── database/    # MCP database tests
│   └── integration/     # MCP integration tests
│
├── pm_providers/        # PM provider tests
│   ├── unit/
│   │   ├── openproject/ # OpenProject provider tests
│   │   ├── jira/        # JIRA provider tests
│   │   ├── clickup/     # ClickUp provider tests
│   │   └── internal/    # Internal provider tests
│   └── integration/     # PM provider integration tests
│
└── shared/              # Shared code tests
    ├── unit/
    │   ├── database/    # Database connection tests
    │   └── config/      # Shared config tests
    └── integration/
```

## Benefits

1. **Clear Ownership**: Each test clearly belongs to a service
2. **Easier Navigation**: Find tests by service, not by module
3. **Independent Testing**: Can test each service independently
4. **Better CI/CD**: Can run tests per service in parallel
5. **Matches Code Structure**: Tests mirror the code organization

## Migration Strategy

1. Create new directory structure
2. Move tests to appropriate service directories
3. Update imports in test files
4. Update pytest configuration
5. Update CI/CD scripts
6. Verify all tests still pass

## Test File Mapping

### Backend Tests
- `tests/unit/server/*` → `tests/backend/unit/server/*`
- `tests/unit/agents/*` → `tests/backend/unit/agents/*`
- `tests/unit/graph/*` → `tests/backend/unit/graph/*`
- `tests/unit/tools/*` → `tests/backend/unit/tools/*`
- `tests/unit/config/*` → `tests/backend/unit/config/*`
- `tests/unit/llms/*` → `tests/backend/unit/llms/*`
- `tests/unit/rag/*` → `tests/backend/unit/rag/*`
- `tests/unit/crawler/*` → `tests/backend/unit/crawler/*`
- `tests/unit/utils/*` → `tests/backend/unit/utils/*`
- `tests/test_deerflow.py` → `tests/backend/test_deerflow.py`
- `tests/test_conversation_flow.py` → `tests/backend/test_conversation_flow.py`
- `tests/test_api.py` → `tests/backend/test_api.py`
- `tests/test_analytics.py` → `tests/backend/test_analytics.py`
- `tests/integration/test_nodes.py` → `tests/backend/integration/test_nodes.py`

### MCP Server Tests
- `tests/unit/server/test_mcp_*.py` → `tests/mcp_server/unit/server/test_mcp_*.py`
- Create new tests for MCP server components

### PM Provider Tests
- `tests/test_pm_features.py` → `tests/pm_providers/test_pm_features.py`
- Create new tests for PM providers

### Shared Tests
- Database connection tests → `tests/shared/unit/database/`
- Shared config tests → `tests/shared/unit/config/`

