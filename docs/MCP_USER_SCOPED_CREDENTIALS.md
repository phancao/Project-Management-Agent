# MCP Server User-Scoped Credentials

This document explains how to implement user-scoped credential loading for the PM MCP Server, allowing each user to have their own credentials when connecting to external PM systems.

## Problem Statement

When multiple users connect to the MCP Server, each user should only access their own PM provider credentials. Currently, the server loads all active providers without user filtering.

## Solution Architecture

### 1. User Identification in MCP Protocol

The MCP protocol doesn't have built-in user authentication. We need to add user context through:

**Option A: HTTP Headers (SSE Transport)**
- Client sends `X-User-ID` or `Authorization` header
- Server extracts user ID from header
- Use user ID to filter providers

**Option B: MCP Initialization Options**
- Pass user context in MCP initialization
- Store in connection context
- Use throughout session

**Option C: Per-Request User Context**
- Each tool call includes user context
- More flexible but requires protocol extension

### 2. Database Schema

The `pm_provider_connections` table already has `created_by` field:

```sql
CREATE TABLE pm_provider_connections (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    provider_type VARCHAR(50) NOT NULL,
    base_url VARCHAR(500) NOT NULL,
    api_key VARCHAR(500),
    api_token VARCHAR(500),
    username VARCHAR(255),
    created_by UUID REFERENCES users(id),  -- ✅ Already exists!
    is_active BOOLEAN DEFAULT TRUE,
    ...
);
```

### 3. Implementation Plan

#### Step 1: Add User Context to MCP Server

Modify `PMMCPServer` to accept and store user context:

```python
# src/mcp_servers/pm_server/server.py
class PMMCPServer:
    def __init__(self, config: PMServerConfig | None = None, user_id: str | None = None):
        self.config = config or PMServerConfig.from_env()
        self.user_id = user_id  # Store user context
        # ... rest of initialization
    
    def _initialize_pm_handler(self) -> None:
        """Initialize PM Handler with user-scoped database session."""
        if self.pm_handler is not None:
            return
        
        self.db_session = next(get_db_session())
        
        # Create user-scoped PMHandler
        if self.user_id:
            self.pm_handler = PMHandler.from_db_session_and_user(
                self.db_session, 
                user_id=self.user_id
            )
        else:
            # Fallback: all providers (for backward compatibility)
            self.pm_handler = PMHandler.from_db_session(self.db_session)
```

#### Step 2: Modify PMHandler to Filter by User

```python
# src/server/pm_handler.py
class PMHandler:
    def __init__(
        self, 
        db_session: Optional[Session] = None,
        single_provider: Optional[BasePMProvider] = None,
        user_id: Optional[str] = None  # Add user_id parameter
    ):
        self.db = db_session
        self.single_provider = single_provider
        self.user_id = user_id  # Store user ID
        self._mode = "single" if single_provider else "multi"
    
    def _get_active_providers(self) -> List[PMProviderConnection]:
        """Get active PM providers, filtered by user if user_id is set."""
        if not self.db:
            return []
        
        query = self.db.query(PMProviderConnection).filter(
            PMProviderConnection.is_active.is_(True)
        )
        
        # Filter by user if user_id is provided
        if self.user_id:
            query = query.filter(
                PMProviderConnection.created_by == self.user_id
            )
        
        return query.all()
    
    @classmethod
    def from_db_session_and_user(
        cls,
        db_session: Session,
        user_id: str
    ) -> "PMHandler":
        """Create PMHandler instance for specific user."""
        return cls(db_session=db_session, user_id=user_id)
```

#### Step 3: Extract User from SSE Connection

```python
# src/mcp_servers/pm_server/transports/sse.py
@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint with user authentication."""
    # Extract user ID from header or query parameter
    user_id = request.headers.get("X-User-ID") or request.query_params.get("user_id")
    
    # Or from Authorization header (JWT token)
    # auth_header = request.headers.get("Authorization")
    # user_id = extract_user_from_token(auth_header)
    
    if not user_id:
        return StreamingResponse(
            iter([_make_sse_event("error", {"error": "User ID required"})]),
            media_type="text/event-stream"
        )
    
    # Create user-scoped MCP server instance
    mcp_server = PMMCPServer(user_id=user_id)
    # ... rest of SSE handling
```

#### Step 4: Store User Context Per Connection

```python
# src/mcp_servers/pm_server/transports/sse.py
# Store user context per SSE connection
connection_user_map = {}

@app.get("/sse")
async def sse_endpoint(request: Request):
    user_id = extract_user_id(request)
    connection_id = generate_connection_id()
    connection_user_map[connection_id] = user_id
    
    # Store in app state
    if not hasattr(app.state, 'connection_users'):
        app.state.connection_users = {}
    app.state.connection_users[connection_id] = user_id
    
    # Create user-scoped PMHandler
    mcp_server = PMMCPServer(user_id=user_id)
    # ...
```

## Implementation Example

### Complete Flow

```python
# 1. Client connects with user identification
# GET /sse?user_id=123e4567-e89b-12d3-a456-426614174000
# OR
# GET /sse
# Headers: X-User-ID: 123e4567-e89b-12d3-a456-426614174000

# 2. Server extracts user ID
user_id = request.headers.get("X-User-ID") or request.query_params.get("user_id")

# 3. Create user-scoped PMHandler
pm_handler = PMHandler.from_db_session_and_user(db_session, user_id=user_id)

# 4. Query only user's providers
providers = db.query(PMProviderConnection).filter(
    PMProviderConnection.is_active == True,
    PMProviderConnection.created_by == user_id
).all()

# 5. Use user's credentials for API calls
for provider in providers:
    jira_provider = JIRAProvider(provider.config)
    projects = await jira_provider.list_projects()  # Uses user's credentials
```

## Security Considerations

### 1. Authentication
- **JWT Tokens**: Extract user from JWT in Authorization header
- **Session Tokens**: Use session-based authentication
- **API Keys**: User-specific API keys for MCP access

### 2. Authorization
- Verify user has permission to access provider
- Check `created_by` matches authenticated user
- Prevent user from accessing other users' providers

### 3. Credential Isolation
- Each user's credentials stored separately
- No credential leakage between users
- User can only see their own providers

## Database Queries

### Get User's Providers
```sql
SELECT * FROM pm_provider_connections
WHERE is_active = TRUE
  AND created_by = 'user-uuid-here';
```

### Add Provider for User
```sql
INSERT INTO pm_provider_connections (
    id, name, provider_type, base_url, api_token, username, created_by, is_active
) VALUES (
    gen_random_uuid(),
    'My JIRA',
    'jira',
    'https://company.atlassian.net',
    'user-api-token',
    'user@company.com',
    'user-uuid-here',  -- User's UUID
    TRUE
);
```

## API Endpoints

### Add Provider (User-Scoped)
```bash
POST /api/pm/providers
Authorization: Bearer <jwt-token>
Content-Type: application/json

{
  "name": "My JIRA",
  "provider_type": "jira",
  "base_url": "https://company.atlassian.net",
  "api_token": "user-token",
  "username": "user@company.com"
}
# Server automatically sets created_by from JWT token
```

### List User's Providers
```bash
GET /api/pm/providers
Authorization: Bearer <jwt-token>

# Returns only providers where created_by = user_id from token
```

## MCP Client Configuration

### Cursor Configuration
```json
{
  "mcpServers": {
    "pm-server": {
      "url": "http://localhost:8080/sse",
      "transport": "sse",
      "headers": {
        "X-User-ID": "user-uuid-here"
      }
    }
  }
}
```

### Or with JWT
```json
{
  "mcpServers": {
    "pm-server": {
      "url": "http://localhost:8080/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer <jwt-token>"
      }
    }
  }
}
```

## Migration Path

### Phase 1: Add User Filtering (Backward Compatible)
- Add `user_id` parameter to PMHandler
- If `user_id` is None, load all providers (backward compatible)
- If `user_id` is provided, filter by user

### Phase 2: Add User Context to MCP Server
- Extract user from headers/query params
- Pass to PMHandler
- Store per connection

### Phase 3: Enforce User Authentication
- Require user identification for all connections
- Remove backward compatibility mode
- Add authentication middleware

## Testing

### Test User Isolation
```python
# User A's providers
user_a_id = "user-a-uuid"
handler_a = PMHandler.from_db_session_and_user(db, user_a_id)
providers_a = handler_a._get_active_providers()
# Should only return User A's providers

# User B's providers
user_b_id = "user-b-uuid"
handler_b = PMHandler.from_db_session_and_user(db, user_b_id)
providers_b = handler_b._get_active_providers()
# Should only return User B's providers
# Should NOT include User A's providers
```

## Summary

1. **User Identification**: Extract from HTTP headers or query parameters
2. **Database Filtering**: Filter `pm_provider_connections` by `created_by = user_id`
3. **Per-Connection Context**: Store user ID per MCP connection
4. **Security**: Verify user authentication and authorization
5. **Isolation**: Each user only sees their own providers and credentials

This ensures that when User A connects to the MCP Server, they only see and use their own JIRA/OpenProject credentials, and User B sees only their own credentials.









