# How MCP Server Loads User's JIRA Credentials

This document explains the **exact mechanism** of how the MCP Server loads a user's JIRA credentials when Cursor connects.

## Complete Code Flow

### Step 1: Cursor Connects with MCP API Key

```
Cursor → GET /sse
Headers:
  X-MCP-API-Key: mcp_a1b2c3d4e5f6...
```

**Code Location**: `mcp_server/transports/sse.py:390-405`

```python
@app.get("/sse")
async def sse_endpoint(request: Request):
    # Extract API key from header
    api_key = request.headers.get("X-MCP-API-Key")
    
    # Validate API key and get user_id
    from ..auth import validate_mcp_api_key
    user_id = await validate_mcp_api_key(api_key)
    # Returns: "123e4567-e89b-12d3-a456-426614174000"
```

**What `validate_mcp_api_key()` does**:
```python
# mcp_server/auth.py:18-63

async def validate_mcp_api_key(api_key: str) -> Optional[str]:
    # Query database
    key_record = db.query(UserMCPAPIKey).filter(
        UserMCPAPIKey.api_key == api_key,
        UserMCPAPIKey.is_active == True
    ).first()
    
    # Returns user_id from the record
    return str(key_record.user_id)  # "123e4567-e89b-12d3-a456-426614174000"
```

### Step 2: Create User-Scoped MCP Server

**Code Location**: `mcp_server/transports/sse.py:427-438`

```python
# Create user-scoped MCP server instance
mcp_server = PMMCPServer(config=user_config, user_id=user_id)
# user_id = "123e4567-e89b-12d3-a456-426614174000"

# Initialize PM handler with user context
mcp_server._initialize_pm_handler()
```

**What `_initialize_pm_handler()` does**:
```python
# mcp_server/server.py:77-104

def _initialize_pm_handler(self) -> None:
    # Get database session
    self.db_session = next(get_db_session())
    
    # Initialize PMHandler with user context
    if self.user_id:  # user_id = "123e4567-e89b-12d3-a456-426614174000"
        self.pm_handler = PMHandler.from_db_session_and_user(
            self.db_session, 
            user_id=self.user_id  # ✅ Pass user_id to PMHandler
        )
```

**What `PMHandler.from_db_session_and_user()` does**:
```python
# backend/server/pm_handler.py:122-141

@classmethod
def from_db_session_and_user(cls, db_session: Session, user_id: str):
    return cls(db_session=db_session, user_id=user_id)
    # ✅ PMHandler now has self.user_id = "123e4567-e89b-12d3-a456-426614174000"
```

### Step 3: Load User's Providers from Database

**When a tool is called (e.g., `list_projects`)**:

**Code Location**: `backend/server/pm_handler.py:277-320`

```python
async def list_all_projects(self) -> List[Dict[str, Any]]:
    # Get active providers for THIS user
    providers = self._get_active_providers()  # ← This is where it happens!
```

**What `_get_active_providers()` does**:
```python
# backend/server/pm_handler.py:143-166

def _get_active_providers(self) -> List[PMProviderConnection]:
    if not self.db:
        return []
    
    # Build query
    query = self.db.query(PMProviderConnection).filter(
        PMProviderConnection.is_active.is_(True)
    )
    
    # ✅ Filter by user_id if set
    if self.user_id:  # self.user_id = "123e4567-e89b-12d3-a456-426614174000"
        query = query.filter(
            PMProviderConnection.created_by == self.user_id
        )
        # SQL: WHERE is_active = TRUE AND created_by = '123e4567-e89b-12d3-a456-426614174000'
    
    providers = query.all()  # ✅ Returns only this user's providers
    return providers
```

**Database Query Executed**:
```sql
SELECT * FROM pm_provider_connections
WHERE is_active = TRUE
  AND created_by = '123e4567-e89b-12d3-a456-426614174000';
```

**Returns**:
```python
[
    PMProviderConnection(
        id='provider-uuid-1',
        provider_type='jira',
        base_url='https://company.atlassian.net',
        api_token='ATATT3xFfGF0abc123...',  # ✅ User's JIRA token
        username='user@company.com',         # ✅ User's email
        created_by='123e4567-e89b-12d3-a456-426614174000',  # ✅ Matches!
        is_active=True
    )
]
```

### Step 4: Create Provider Instance with Credentials

**Code Location**: `backend/server/pm_handler.py:168-201`

```python
def _create_provider_instance(self, provider: PMProviderConnection):
    # Extract credentials from database record
    api_token_value = provider.api_token  # "ATATT3xFfGF0abc123..."
    username_value = provider.username    # "user@company.com"
    base_url = provider.base_url          # "https://company.atlassian.net"
    
    # Create JIRA provider instance with user's credentials
    return create_pm_provider(
        provider_type="jira",
        base_url=base_url,
        api_token=api_token_value,  # ✅ User's JIRA token
        username=username_value      # ✅ User's email
    )
```

**What `create_pm_provider()` does**:
```python
# pm_providers/factory.py:18-64

def create_pm_provider(...):
    config = PMProviderConfig(
        provider_type="jira",
        base_url="https://company.atlassian.net",
        api_token="ATATT3xFfGF0abc123...",  # ✅ User's token
        username="user@company.com"         # ✅ User's email
    )
    
    return JIRAProvider(config)  # ✅ JIRA provider with user's credentials
```

**What `JIRAProvider.__init__()` does**:
```python
# pm_providers/jira.py:29-54

def __init__(self, config: PMProviderConfig):
    self.base_url = config.base_url  # "https://company.atlassian.net"
    api_token = config.api_token      # "ATATT3xFfGF0abc123..."
    email = config.username           # "user@company.com"
    
    # Create Basic Auth header
    auth_string = f"{email}:{api_token}"
    auth_b64 = base64.b64encode(auth_string.encode()).decode()
    
    self.headers = {
        "Authorization": f"Basic {auth_b64}",  # ✅ Ready to call JIRA API
        "Content-Type": "application/json"
    }
```

### Step 5: Use Credentials to Call JIRA API

**When `list_projects` is called**:

```python
# backend/server/pm_handler.py:358-360

for provider in providers:  # Only user's providers
    provider_instance = self._create_provider_instance(provider)
    # ✅ provider_instance has user's JIRA credentials
    
    projects = await provider_instance.list_projects()
    # ✅ Calls JIRA API with user's credentials
```

**JIRA API Call**:
```python
# pm_providers/jira.py:list_projects()

url = f"{self.base_url}/rest/api/3/project"
# self.base_url = "https://company.atlassian.net"
# self.headers = {"Authorization": "Basic <user's-credentials>"}

response = requests.get(url, headers=self.headers)
# ✅ Uses user's JIRA API token to authenticate
```

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Cursor Connects                                    │
└─────────────────────────────────────────────────────────────┘

Cursor → GET /sse
Headers: X-MCP-API-Key: mcp_xxx

┌─────────────────────────────────────────────────────────────┐
│  Step 2: Validate API Key → Get user_id                    │
└─────────────────────────────────────────────────────────────┘

validate_mcp_api_key("mcp_xxx")
  ↓
Query: SELECT user_id FROM user_mcp_api_keys WHERE api_key = 'mcp_xxx'
  ↓
Returns: user_id = "123e4567-e89b-12d3-a456-426614174000"

┌─────────────────────────────────────────────────────────────┐
│  Step 3: Create User-Scoped MCP Server                      │
└─────────────────────────────────────────────────────────────┘

mcp_server = PMMCPServer(user_id="123e4567-e89b-12d3-a456-426614174000")
mcp_server._initialize_pm_handler()
  ↓
pm_handler = PMHandler.from_db_session_and_user(db, user_id="...")
  ↓
pm_handler.user_id = "123e4567-e89b-12d3-a456-426614174000"  ✅

┌─────────────────────────────────────────────────────────────┐
│  Step 4: Load User's Providers from Database                │
└─────────────────────────────────────────────────────────────┘

pm_handler._get_active_providers()
  ↓
Query: SELECT * FROM pm_provider_connections
       WHERE is_active = TRUE
         AND created_by = '123e4567-e89b-12d3-a456-426614174000'
  ↓
Returns: [
    PMProviderConnection(
        provider_type='jira',
        base_url='https://company.atlassian.net',
        api_token='ATATT3xFfGF0abc123...',  ✅ User's token
        username='user@company.com',         ✅ User's email
        created_by='123e4567-e89b-12d3-a456-426614174000'
    )
]

┌─────────────────────────────────────────────────────────────┐
│  Step 5: Create Provider Instance with Credentials         │
└─────────────────────────────────────────────────────────────┘

pm_handler._create_provider_instance(provider)
  ↓
create_pm_provider(
    provider_type="jira",
    base_url="https://company.atlassian.net",
    api_token="ATATT3xFfGF0abc123...",  ✅ From database
    username="user@company.com"          ✅ From database
)
  ↓
JIRAProvider(config)
  ↓
self.headers = {
    "Authorization": "Basic <base64(user@company.com:ATATT3x...)>"
}

┌─────────────────────────────────────────────────────────────┐
│  Step 6: Call JIRA API with User's Credentials              │
└─────────────────────────────────────────────────────────────┘

provider_instance.list_projects()
  ↓
GET https://company.atlassian.net/rest/api/3/project
Headers: Authorization: Basic <user's-credentials>
  ↓
JIRA API returns user's projects
```

## Key Code Locations

1. **API Key Validation**: `mcp_server/auth.py:validate_mcp_api_key()`
   - Queries `user_mcp_api_keys` table
   - Returns `user_id`

2. **User-Scoped Server**: `mcp_server/server.py:_initialize_pm_handler()`
   - Creates `PMHandler` with `user_id`
   - Stores `user_id` in `pm_handler.user_id`

3. **Load Providers**: `backend/server/pm_handler.py:_get_active_providers()`
   - Queries `pm_provider_connections` table
   - Filters by `created_by = user_id`
   - Returns only user's providers

4. **Create Provider**: `backend/server/pm_handler.py:_create_provider_instance()`
   - Extracts credentials from database record
   - Creates `JIRAProvider` instance with credentials

5. **Use Credentials**: `pm_providers/jira.py:JIRAProvider.__init__()`
   - Creates Basic Auth header with user's token
   - Ready to call JIRA API

## Summary

**How MCP Server loads user's JIRA credentials:**

1. ✅ **Cursor connects** with MCP API key
2. ✅ **Server validates** API key → gets `user_id` from database
3. ✅ **Server creates** user-scoped `PMHandler` with `user_id`
4. ✅ **PMHandler queries** database: `WHERE created_by = user_id`
5. ✅ **Returns** only user's JIRA credentials from `pm_provider_connections`
6. ✅ **Creates** `JIRAProvider` instance with user's `api_token` and `username`
7. ✅ **Uses** credentials to authenticate JIRA API calls

**The key is**: The `user_id` flows from MCP API key → PMHandler → Database query filter → Only user's credentials are loaded.









