# MCP Server Authentication for External Clients

This document explains how external clients like Cursor can authenticate and identify users when connecting to the PM MCP Server.

## Important: Two Types of API Keys

⚠️ **Do not confuse these two different keys:**

1. **MCP API Key** - For Cursor to authenticate to MCP Server (this document)
2. **PM Provider API Key** - For MCP Server to authenticate to JIRA/OpenProject (stored separately)

See `docs/MCP_KEY_TYPES_EXPLAINED.md` for detailed comparison.

## Problem Statement

When external systems (Cursor, VS Code, etc.) connect to the PM MCP Server, they need to:
1. **Authenticate** - Prove they are authorized to access the server
2. **Identify User** - Tell the server which user they represent
3. **Access User's Credentials** - Server loads only that user's PM provider credentials

## Solution: MCP API Keys (Not PM Provider Keys!)

Each user gets a unique **MCP API Key** that:
- Identifies the user to the MCP Server
- Authenticates the connection from Cursor/VS Code
- Allows the server to load that user's PM provider credentials

**Note**: This is different from PM Provider API keys (JIRA tokens, OpenProject keys) which are stored in `pm_provider_connections` and used by the MCP Server to call external APIs.

## Implementation

### 1. Database Schema

Add a table to store user API keys:

```sql
-- User API Keys for MCP Server access
CREATE TABLE user_mcp_api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    api_key VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),  -- Optional: "Cursor", "VS Code", etc.
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,  -- Optional: for key expiration
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_mcp_api_keys_user_id ON user_mcp_api_keys(user_id);
CREATE INDEX idx_user_mcp_api_keys_api_key ON user_mcp_api_keys(api_key);
```

### 2. API Key Generation

**Via API Endpoint:**
```bash
POST /api/users/{user_id}/mcp-keys
Authorization: Bearer <user-jwt-token>
Content-Type: application/json

{
  "name": "Cursor Desktop"
}

# Response:
{
  "api_key": "mcp_abc123def456...",
  "user_id": "user-uuid",
  "name": "Cursor Desktop",
  "created_at": "2025-01-20T10:00:00Z"
}
```

**Via SQL:**
```sql
INSERT INTO user_mcp_api_keys (user_id, api_key, name, is_active)
VALUES (
    'user-uuid-here',
    'mcp_' || encode(gen_random_bytes(32), 'hex'),
    'Cursor Desktop',
    TRUE
);
```

### 3. MCP Server Authentication

Modify SSE endpoint to authenticate via API key:

```python
# mcp_server/transports/sse.py

@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint with API key authentication."""
    
    # Extract API key from header
    api_key = request.headers.get("X-MCP-API-Key") or request.headers.get("Authorization")
    
    # Handle "Bearer mcp_xxx" format
    if api_key and api_key.startswith("Bearer "):
        api_key = api_key[7:]
    
    if not api_key:
        return StreamingResponse(
            iter([_make_sse_event("error", {"error": "API key required"})]),
            media_type="text/event-stream"
        )
    
    # Validate API key and get user
    user_id = await validate_mcp_api_key(api_key)
    if not user_id:
        return StreamingResponse(
            iter([_make_sse_event("error", {"error": "Invalid API key"})]),
            media_type="text/event-stream"
        )
    
    # Update last_used_at
    await update_api_key_usage(api_key)
    
    # Create user-scoped MCP server
    mcp_server = PMMCPServer(user_id=user_id)
    # ... rest of SSE handling
```

### 4. API Key Validation Function

```python
# mcp_server/auth.py

from database.orm_models import UserMCPAPIKey
from database.connection import get_db_session
from sqlalchemy.orm import Session

async def validate_mcp_api_key(api_key: str) -> str | None:
    """
    Validate MCP API key and return user_id.
    
    Args:
        api_key: API key to validate
        
    Returns:
        user_id if valid, None otherwise
    """
    db = next(get_db_session())
    try:
        key_record = db.query(UserMCPAPIKey).filter(
            UserMCPAPIKey.api_key == api_key,
            UserMCPAPIKey.is_active == True
        ).first()
        
        if not key_record:
            return None
        
        # Check expiration
        if key_record.expires_at and key_record.expires_at < datetime.utcnow():
            return None
        
        return str(key_record.user_id)
    finally:
        db.close()

async def update_api_key_usage(api_key: str):
    """Update last_used_at timestamp for API key."""
    db = next(get_db_session())
    try:
        key_record = db.query(UserMCPAPIKey).filter(
            UserMCPAPIKey.api_key == api_key
        ).first()
        
        if key_record:
            key_record.last_used_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
```

## Usage

### For Cursor Users

1. **User logs into web UI** → Gets JWT token
2. **User generates MCP API key** via web UI or API
3. **User copies API key**
4. **User configures Cursor** with API key:

```json
{
  "mcpServers": {
    "pm-server": {
      "url": "http://localhost:8080/sse",
      "transport": "sse",
      "headers": {
        "X-MCP-API-Key": "mcp_abc123def456..."
      }
    }
  }
}
```

### Flow Diagram

```
┌─────────────┐
│   User      │
│  (Browser)  │
└──────┬──────┘
       │
       │ 1. Login → Get JWT
       ▼
┌─────────────────┐
│  Web UI         │
│  /api/users/me/  │
│  mcp-keys       │
└──────┬──────────┘
       │
       │ 2. Generate API Key
       ▼
┌─────────────────┐
│  Database       │
│  user_mcp_      │
│  api_keys       │
└──────┬──────────┘
       │
       │ 3. Copy API Key
       ▼
┌─────────────┐
│   Cursor    │
│  (External) │
└──────┬──────┘
       │
       │ 4. Connect with API Key
       ▼
┌─────────────────┐
│  MCP Server     │
│  /sse           │
└──────┬──────────┘
       │
       │ 5. Validate API Key
       ▼
┌─────────────────┐
│  Database       │
│  Lookup user_id │
└──────┬──────────┘
       │
       │ 6. Load user's providers
       ▼
┌─────────────────┐
│  PMHandler      │
│  (user-scoped)  │
└─────────────────┘
```

## Alternative Solutions

### Option A: JWT Token (Recommended for Web Integration)

If users authenticate via web UI, use JWT tokens:

```python
# Extract user from JWT
auth_header = request.headers.get("Authorization")
if auth_header and auth_header.startswith("Bearer "):
    token = auth_header[7:]
    user_id = extract_user_from_jwt(token)
```

**Pros:**
- No separate API key management
- Uses existing authentication
- Automatic expiration

**Cons:**
- Requires JWT implementation
- Tokens expire (need refresh)

### Option B: OAuth/SSO

For enterprise deployments:

```python
# OAuth callback
@app.get("/auth/oauth/callback")
async def oauth_callback(code: str):
    # Exchange code for token
    # Get user info
    # Create session
    user_id = get_user_from_oauth(code)
    return {"mcp_api_key": generate_api_key(user_id)}
```

### Option C: User-Specific Endpoints

Each user gets their own endpoint:

```
http://localhost:8080/sse/user/{user_id}?token={api_key}
```

**Pros:**
- Simple routing
- Clear user identification

**Cons:**
- URL contains user_id (less secure)
- More endpoints to manage

## Security Considerations

### API Key Security

1. **Key Format**: Use prefix `mcp_` to identify MCP keys
2. **Key Length**: Minimum 32 bytes (64 hex characters)
3. **Key Storage**: Hash keys in database (optional, for extra security)
4. **Key Rotation**: Allow users to regenerate keys
5. **Key Expiration**: Optional expiration dates
6. **Rate Limiting**: Limit requests per API key

### Best Practices

1. **HTTPS Only**: Always use HTTPS in production
2. **Key Rotation**: Encourage periodic key rotation
3. **Key Naming**: Allow users to name keys ("Cursor", "VS Code", etc.)
4. **Revocation**: Allow users to revoke keys
5. **Audit Logging**: Log all API key usage

## Implementation Steps

### Phase 1: Database Schema
1. Create `user_mcp_api_keys` table
2. Add indexes
3. Add ORM model

### Phase 2: API Endpoints
1. `POST /api/users/me/mcp-keys` - Generate key
2. `GET /api/users/me/mcp-keys` - List keys
3. `DELETE /api/users/me/mcp-keys/{key_id}` - Revoke key

### Phase 3: MCP Server Authentication
1. Add API key validation
2. Extract user_id from API key
3. Create user-scoped server instance

### Phase 4: Web UI
1. Add "MCP API Keys" section to user settings
2. Generate/revoke keys UI
3. Copy key to clipboard

## Example: Complete Flow

### 1. User Generates API Key

```bash
# User authenticates via web UI, gets JWT
POST /api/users/me/mcp-keys
Authorization: Bearer <jwt-token>
{
  "name": "Cursor Desktop"
}

# Response
{
  "api_key": "mcp_a1b2c3d4e5f6...",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Cursor Desktop",
  "created_at": "2025-01-20T10:00:00Z"
}
```

### 2. User Configures Cursor

```json
{
  "mcpServers": {
    "pm-server": {
      "url": "https://pm-server.example.com/sse",
      "transport": "sse",
      "headers": {
        "X-MCP-API-Key": "mcp_a1b2c3d4e5f6..."
      }
    }
  }
}
```

### 3. Cursor Connects

```bash
GET /sse
Headers:
  X-MCP-API-Key: mcp_a1b2c3d4e5f6...
```

### 4. Server Validates and Routes

```python
# Server validates API key
user_id = validate_mcp_api_key("mcp_a1b2c3d4e5f6...")
# Returns: "123e4567-e89b-12d3-a456-426614174000"

# Server creates user-scoped handler
pm_handler = PMHandler.from_db_session_and_user(db, user_id=user_id)

# Only user's providers are loaded
providers = pm_handler._get_active_providers()
# Returns only providers where created_by = user_id
```

## Summary

**Solution**: User API Keys stored in database
- Each user can have multiple API keys
- Keys identify user and authenticate connection
- Server validates key → gets user_id → loads user's providers
- External clients (Cursor) use API key in headers

**Benefits**:
- ✅ Secure authentication
- ✅ User identification
- ✅ Multiple keys per user (different clients)
- ✅ Key revocation
- ✅ Audit trail

