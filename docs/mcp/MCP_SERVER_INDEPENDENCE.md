# MCP Server Independence

The MCP Server is now **completely independent** from the backend system.

## Architecture

### Separate Databases

**Backend Database** (`project_management`):
- Backend API tables (projects, tasks, sprints, etc.)
- Backend user management
- Backend conversation sessions

**MCP Server Database** (`mcp_server`):
- MCP Server users (for MCP client authentication)
- MCP Server API keys (`user_mcp_api_keys`)
- PM Provider connections (`pm_provider_connections`)

### Separate Code Modules

**Backend**:
- `backend/server/pm_handler.py` - Backend PM Handler
- `database/connection.py` - Backend database connection
- `database/orm_models.py` - Backend database models

**MCP Server**:
- `mcp_server/pm_handler.py` - MCP Server PM Handler
- `mcp_server/database/connection.py` - MCP Server database connection
- `mcp_server/database/models.py` - MCP Server database models

## Database Schema

### MCP Server Database (`mcp_server`)

**Tables:**
1. `users` - MCP Server users (for Cursor/VS Code connections)
2. `user_mcp_api_keys` - API keys for MCP client authentication
3. `pm_provider_connections` - PM provider credentials (JIRA, OpenProject, etc.)

**Schema File**: `database/mcp_server_schema.sql`

## Docker Configuration

### Separate Database Service

```yaml
# MCP Server Database
mcp_postgres:
  image: pgvector/pgvector:pg15
  environment:
    POSTGRES_DB: mcp_server
    POSTGRES_USER: mcp_user
    POSTGRES_PASSWORD: mcp_password
  ports:
    - "5434:5432"  # Different port from backend (5432)
```

### MCP Server Service

```yaml
pm_mcp_server:
  environment:
    - DATABASE_URL=postgresql://mcp_user:mcp_password@mcp_postgres:5432/mcp_server
  depends_on:
    mcp_postgres:
      condition: service_healthy
```

## Benefits

1. **Complete Independence**: MCP Server can run without backend
2. **Separate Scaling**: Can scale MCP Server independently
3. **Data Isolation**: MCP Server data is separate from backend
4. **No Dependencies**: MCP Server doesn't depend on backend code
5. **Clear Separation**: Easy to understand what belongs where

## Migration Notes

- MCP Server uses its own database connection
- MCP Server has its own PM Handler implementation
- MCP Server has its own database models
- All imports updated to use MCP Server's own modules

## Usage

MCP Server works independently:
- Users connect via Cursor/VS Code with MCP API keys
- Credentials stored in MCP Server's own database
- No dependency on backend system









