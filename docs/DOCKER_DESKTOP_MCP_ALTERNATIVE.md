# Alternative: Using Docker Compose (MCP Toolkit Not Available)

If you don't see the MCP Toolkit in Docker Desktop settings, you can still use the PM MCP Server with Docker Compose. This works just as well and is actually simpler for development!

## ✅ Quick Start with Docker Compose

### Step 1: Start the PM MCP Server

```bash
# Start the server (and its dependencies)
docker-compose up -d pm_mcp_server postgres

# Or start everything
docker-compose up -d
```

### Step 2: Verify It's Running

```bash
# Check container status
docker-compose ps pm_mcp_server

# Check health
curl http://localhost:8080/health

# List tools
curl -X POST http://localhost:8080/tools/list \
  -H "Content-Type: application/json" \
  -d '{}' | jq '.tools | length'
```

### Step 3: Use with AI Clients

Configure your AI client (Claude Desktop, Cursor, etc.) to connect to:

```
Transport: SSE
URL: http://localhost:8080/sse
```

## 📋 Docker Compose Configuration

The PM MCP Server is already configured in `docker-compose.yml`:

```yaml
pm_mcp_server:
  build:
    context: .
    dockerfile: Dockerfile.mcp-server
  environment:
    - DATABASE_URL=postgresql://pm_user:pm_password@postgres:5432/project_management
    - LOG_LEVEL=INFO
    - MCP_TRANSPORT=sse
    - MCP_HOST=0.0.0.0
    - MCP_PORT=8080
  ports:
    - "8080:8080"
  depends_on:
    postgres:
      condition: service_healthy
```

## 🔧 Managing the Server

### Start/Stop

```bash
# Start
docker-compose up -d pm_mcp_server

# Stop
docker-compose stop pm_mcp_server

# Restart
docker-compose restart pm_mcp_server

# View logs
docker-compose logs -f pm_mcp_server
```

### Update Configuration

Edit `docker-compose.yml` and restart:

```bash
docker-compose up -d --build pm_mcp_server
```

## 🎯 Why Docker Compose is Actually Better

1. **Full Control**: You control all configuration in one file
2. **Integrated**: Works seamlessly with other services (postgres, redis, etc.)
3. **Version Control**: Configuration is in git
4. **No UI Required**: Everything via command line
5. **Same Functionality**: Works identically to MCP Toolkit

## 🔍 Finding MCP Toolkit (If It Exists)

If you want to try finding the MCP Toolkit in Docker Desktop:

1. **Check Extensions Tab**: Settings → Extensions
2. **Check Beta Features**: Settings → General → Enable beta features
3. **Check Experimental**: Settings → General → Experimental features
4. **Search Settings**: Use the search bar in Settings
5. **Check Updates**: Make sure Docker Desktop is fully updated

## 💡 Recommendation

**Use Docker Compose** - it's simpler, more flexible, and works perfectly for your use case. The MCP Toolkit is mainly useful for discovering and installing public MCP servers from a catalog, but since you're using a private/local server, Docker Compose is the better choice.

## 📚 Next Steps

1. ✅ Start the server: `docker-compose up -d pm_mcp_server`
2. ✅ Test it: `curl http://localhost:8080/health`
3. ✅ Configure AI clients to use `http://localhost:8080/sse`
4. ✅ Start using the 53 PM tools!










