# MCP Server Credentials Management

This document explains how the PM MCP Server retrieves and stores credentials for external PM providers (JIRA, OpenProject, ClickUp, etc.) to make API queries.

## Overview

The PM MCP Server supports **two methods** for credential storage:

1. **Database Storage** (Multi-provider mode) - Credentials stored in PostgreSQL database
2. **Environment Variables** (Single-provider mode) - Credentials from `.env` file

## Method 1: Database Storage (Recommended for Multi-Provider)

### Storage Location

Credentials are stored in the **PostgreSQL database** in the `pm_provider_connections` table:

```sql
CREATE TABLE pm_provider_connections (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    provider_type VARCHAR(50) NOT NULL,  -- 'jira', 'openproject', 'clickup', etc.
    base_url VARCHAR(500) NOT NULL,
    api_key VARCHAR(500),                 -- For OpenProject, ClickUp
    api_token VARCHAR(500),               -- For JIRA
    username VARCHAR(255),               -- For JIRA (email)
    organization_id VARCHAR(255),         -- For ClickUp
    workspace_id VARCHAR(255),           -- For OpenProject
    additional_config JSON,              -- Extra configuration
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_sync_at TIMESTAMP
);
```

### How Credentials are Retrieved

1. **PMHandler Initialization** (`src/server/pm_handler.py`):
   ```python
   # PMHandler queries the database for active providers
   def _get_active_providers(self) -> List[PMProviderConnection]:
       return self.db.query(PMProviderConnection).filter(
           PMProviderConnection.is_active.is_(True)
       ).all()
   ```

2. **Provider Instance Creation**:
   ```python
   def _create_provider_instance(self, provider: PMProviderConnection):
       # Extracts credentials from database record
       return create_pm_provider(
           provider_type=provider.provider_type,
           base_url=provider.base_url,
           api_key=provider.api_key,      # Retrieved from DB
           api_token=provider.api_token,   # Retrieved from DB
           username=provider.username,      # Retrieved from DB
           organization_id=provider.organization_id,
           workspace_id=provider.workspace_id,
       )
   ```

3. **API Calls**:
   - Each provider instance uses the credentials to authenticate API requests
   - Credentials are stored in memory only during the request lifecycle
   - Never logged or exposed in responses

### Adding Credentials to Database

**Via API** (Recommended):
```bash
POST /api/pm/providers
Content-Type: application/json

{
  "name": "My JIRA Instance",
  "provider_type": "jira",
  "base_url": "https://your-domain.atlassian.net",
  "api_token": "your-api-token",
  "username": "your-email@example.com"
}
```

**Via SQL** (Direct):
```sql
INSERT INTO pm_provider_connections (
    id, name, provider_type, base_url, api_token, username, is_active
) VALUES (
    gen_random_uuid(),
    'My JIRA',
    'jira',
    'https://your-domain.atlassian.net',
    'your-api-token',
    'your-email@example.com',
    TRUE
);
```

## Method 2: Environment Variables (Single Provider)

### Storage Location

Credentials are stored in the **`.env` file** in the project root:

```bash
# .env file
PM_PROVIDER=jira  # or 'openproject', 'clickup', etc.

# JIRA Configuration
JIRA_URL=https://your-domain.atlassian.net
JIRA_API_TOKEN=your-api-token
JIRA_USERNAME=your-email@example.com

# OpenProject Configuration
OPENPROJECT_URL=https://your-instance.openproject.com
OPENPROJECT_API_KEY=base64-encoded-api-key

# ClickUp Configuration
CLICKUP_API_KEY=your-api-key
CLICKUP_TEAM_ID=your-team-id
```

### How Credentials are Retrieved

1. **Builder Function** (`src/pm_providers/builder.py`):
   ```python
   def build_pm_provider(db_session: Optional[Session] = None):
       provider_type = SELECTED_PM_PROVIDER  # From PM_PROVIDER env var
       
       if provider_type == PMProvider.JIRA.value:
           config = PMProviderConfig(
               provider_type="jira",
               base_url=_get_env("JIRA_URL"),           # From .env
               api_token=_get_env("JIRA_API_TOKEN"),    # From .env
               username=_get_env("JIRA_USERNAME")       # From .env
           )
           return JIRAProvider(config)
   ```

2. **Environment Variable Retrieval**:
   ```python
   def _get_env(key: str) -> str:
       import os
       return os.getenv(key, "")  # Reads from .env file
   ```

## Credential Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server Request                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              PMHandler Initialization                        │
│  (src/server/pm_handler.py)                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌───────────────┐          ┌──────────────────────┐
│ Multi-Provider│          │  Single-Provider     │
│    Mode       │          │      Mode            │
└───────┬───────┘          └──────────┬───────────┘
        │                             │
        │                             │
        ▼                             ▼
┌──────────────────┐        ┌────────────────────┐
│ Query Database   │        │ Read .env file     │
│ pm_provider_     │        │ Environment        │
│ connections      │        │ Variables          │
└───────┬──────────┘        └──────────┬─────────┘
        │                             │
        │                             │
        ▼                             ▼
┌──────────────────────────────────────────────┐
│      Extract Credentials                      │
│  - api_key / api_token                        │
│  - username                                  │
│  - base_url                                  │
│  - organization_id / workspace_id            │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│    Create Provider Instance                  │
│  (JIRAProvider, OpenProjectProvider, etc.)   │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│    Make API Calls to External System         │
│  - Uses credentials for authentication       │
│  - JIRA: Basic Auth (email:token)            │
│  - OpenProject: API Key in headers            │
│  - ClickUp: API Key in headers               │
└──────────────────────────────────────────────┘
```

## Authentication Methods by Provider

### JIRA
- **Method**: Basic Authentication
- **Format**: `base64(email:api_token)`
- **Headers**: `Authorization: Basic <encoded>`
- **Storage**: `api_token` + `username` (email)

### OpenProject
- **Method**: API Key Authentication
- **Format**: Base64-encoded `"apikey:token"`
- **Headers**: `Authorization: Basic <base64-encoded-key>`
- **Storage**: `api_key` (pre-encoded)

### ClickUp
- **Method**: API Key Authentication
- **Headers**: `Authorization: <api_key>`
- **Storage**: `api_key` + `organization_id`

## Security Considerations

### Database Storage
- ✅ Credentials encrypted at rest (PostgreSQL)
- ✅ Access controlled via database permissions
- ✅ Credentials never logged
- ✅ Only active connections are used

### Environment Variables
- ✅ Stored in `.env` file (not committed to git)
- ✅ Loaded at runtime
- ✅ Never exposed in logs
- ⚠️ Ensure `.env` has proper file permissions (600)

### Best Practices
1. **Never commit credentials** to version control
2. **Use database storage** for production (multi-provider support)
3. **Rotate credentials** regularly
4. **Use least-privilege** API tokens
5. **Monitor API usage** for anomalies

## Example: Adding a JIRA Provider

### Via Database (Recommended)
```python
from database.orm_models import PMProviderConnection
from database import get_db_session

db = next(get_db_session())
provider = PMProviderConnection(
    name="Production JIRA",
    provider_type="jira",
    base_url="https://company.atlassian.net",
    api_token="your-api-token-here",
    username="user@company.com",
    is_active=True
)
db.add(provider)
db.commit()
```

### Via Environment Variables
```bash
# .env file
PM_PROVIDER=jira
JIRA_URL=https://company.atlassian.net
JIRA_API_TOKEN=your-api-token-here
JIRA_USERNAME=user@company.com
```

## Troubleshooting

### No Projects Found
1. Check if provider is active: `SELECT * FROM pm_provider_connections WHERE is_active = TRUE;`
2. Verify credentials are correct
3. Test API connection manually
4. Check provider logs for authentication errors

### Authentication Errors
1. Verify API token/key is valid
2. Check token hasn't expired
3. Ensure base_url is correct
4. For JIRA: verify email matches token owner

### Environment Variables Not Loading
1. Ensure `.env` file exists in project root
2. Check variable names match exactly (case-sensitive)
3. Restart server after changing `.env`
4. Verify `PM_PROVIDER` is set correctly

## API Endpoints for Credential Management

- `GET /api/pm/providers` - List all providers
- `POST /api/pm/providers` - Add new provider (stores in database)
- `PUT /api/pm/providers/{id}` - Update provider credentials
- `DELETE /api/pm/providers/{id}` - Deactivate provider
- `POST /api/pm/providers/{id}/test` - Test connection

## Summary

- **Database Storage**: Used by PMHandler in multi-provider mode, supports multiple providers simultaneously
- **Environment Variables**: Used by `build_pm_provider()` for single-provider mode
- **Credentials are never logged** or exposed in API responses
- **Each provider instance** uses credentials only for the duration of API calls
- **Security**: Credentials stored securely, access controlled, never committed to git

