# MCP Server Authentication for Backend

## Security Requirement

The backend service **MUST** authenticate when connecting to the PM MCP Server because:

1. **Sensitive Credentials**: The MCP server stores sensitive provider credentials:
   - JIRA API tokens
   - OpenProject API keys
   - ClickUp API keys
   - Other PM provider authentication secrets

2. **Security Risk**: Without authentication, any service on the Docker network could:
   - Access all stored provider credentials
   - Configure new providers
   - Retrieve sensitive project/task data

3. **Best Practice**: Even for internal Docker network connections, authentication is required for services that handle sensitive data.

## Implementation

### 1. Generate API Key

Generate a secure API key for the backend service:

```bash
python3 -c "import secrets; print('mcp_' + secrets.token_bytes(32).hex())"
```

This generates a key in format: `mcp_<64-hex-characters>`

### 2. Store API Key in MCP Server Database

The API key must be registered in the MCP server's database. You can:

**Option A: Use the MCP server's API key management (recommended)**
- Create a system user in the MCP server database
- Generate an API key for that user using the MCP server's API

**Option B: Insert directly into database (for initial setup)**
```sql
-- First, create a system user (if not exists)
INSERT INTO users (id, email, name, created_at, updated_at)
VALUES (
    '00000000-0000-0000-0000-000000000000'::uuid,
    'system@backend',
    'Backend Service',
    NOW(),
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- Then create the API key
INSERT INTO user_mcp_api_keys (id, user_id, api_key, name, is_active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000'::uuid,
    'mcp_YOUR_GENERATED_KEY_HERE',
    'Backend Service API Key',
    true,
    NOW(),
    NOW()
);
```

### 3. Configure Backend Environment

Add the API key to your backend environment:

**docker-compose.yml:**
```yaml
services:
  api:
    environment:
      - PM_MCP_API_KEY=mcp_YOUR_GENERATED_KEY_HERE
```

**Or via .env file:**
```bash
PM_MCP_API_KEY=mcp_YOUR_GENERATED_KEY_HERE
```

### 4. Verify Authentication

Check backend logs for:
- ✅ `[PM-CHAT] Adding MCP API key to headers for backend authentication`
- ✅ `[SSE] User identified via API key: <user_id>`

If you see warnings:
- ❌ `PM_MCP_API_KEY not set! Backend connection to MCP server is unauthenticated`

## Security Best Practices

1. **Rotate Keys Regularly**: Change the API key periodically
2. **Use Different Keys**: Use separate keys for different environments (dev, staging, prod)
3. **Monitor Usage**: Check MCP server logs for API key usage
4. **Restrict Access**: Only grant API keys to trusted services
5. **Revoke Compromised Keys**: Immediately revoke any keys that may be compromised

## Troubleshooting

### Backend can't connect to MCP server

1. **Check API key is set**: `docker exec pm-backend-api env | grep PM_MCP_API_KEY`
2. **Verify key in database**: Check `user_mcp_api_keys` table
3. **Check MCP server logs**: Look for authentication errors
4. **Verify key format**: Should start with `mcp_` and be 68 characters total

### Authentication fails

1. **Key not in database**: Ensure key is inserted into `user_mcp_api_keys` table
2. **Key inactive**: Check `is_active = true` in database
3. **Key expired**: Check `expires_at` is NULL or in the future
4. **Wrong format**: Ensure key matches exactly (no extra spaces, correct prefix)

## Related Documentation

- [MCP Server README](../mcp_server/README.md) - General MCP server documentation
- [Authentication Module](../mcp_server/auth.py) - API key validation logic

