# Docker Desktop MCP Toolkit - Step-by-Step Setup Guide

This guide will help you set up the PM MCP Server with Docker Desktop's MCP Toolkit using a private/local image.

## ✅ Prerequisites

- ✅ Docker Desktop installed (you have version 24.0.1)
- ✅ Docker Desktop version 4.48+ (for MCP Toolkit support)
- ✅ PM MCP Server image built locally

## 📋 Step 1: Build and Tag the Image

The image is already built. Let's tag it with a simpler name:

```bash
# Tag the existing image with a simpler name
docker tag project-management-agent-pm_mcp_server:latest pm-mcp-server:latest

# Verify the image exists
docker images | grep pm-mcp-server
```

You should see:
```
pm-mcp-server   latest   <image-id>   <time>   <size>
```

## 📋 Step 2: Prepare Environment Variables

Before configuring Docker Desktop, note down these environment variables:

### Required:
- `DATABASE_URL`: PostgreSQL connection string
  - Format: `postgresql://pm_user:pm_password@postgres:5432/project_management`
  - Or: `postgresql://pm_user:pm_password@localhost:5432/project_management` (if using local DB)

### Optional:
- `LOG_LEVEL`: Logging level (default: `INFO`)
- `ENABLE_AUTH`: Enable authentication (default: `false`)
- `ENABLE_RBAC`: Enable RBAC (default: `false`)
- `MCP_TRANSPORT`: Transport type (default: `sse`)
- `MCP_HOST`: Host to bind (default: `0.0.0.0`)
- `MCP_PORT`: Port to use (default: `8080`)

## 📋 Step 3: Enable MCP Toolkit (If Not Visible)

If you don't see the MCP section in Docker Desktop settings, try these steps:

### Enable Beta/Experimental Features

1. **Open Docker Desktop**
2. **Go to Settings** → **General**
3. **Enable Beta Features** (if available)
4. **Enable Experimental Features** (if available)
5. **Restart Docker Desktop**

### Check Extensions

1. **Go to Settings** → **Extensions**
2. **Look for "MCP Toolkit"** or "MCP" in the list
3. **Install/Enable** if it's available but not enabled

### Alternative: Tag Image with `mcp/` Prefix

Some versions require images to be tagged with `mcp/` prefix:

```bash
docker tag pm-mcp-server:latest mcp/pm-mcp-server:latest
```

Then use `mcp/pm-mcp-server:latest` as the image name in Docker Desktop.

## 📋 Step 4: Configure Docker Desktop MCP Toolkit

### Option A: Using Docker Desktop UI (If Available)

1. **Open Docker Desktop**
   - Launch Docker Desktop application

2. **Navigate to MCP Settings**
   - Click the **Settings** icon (gear) in the top right
   - Go to **Extensions** → **MCP** (or search for "MCP" in settings)
   - If not visible, see Step 3 above

3. **Add Custom MCP Server**
   - Click **"Add Server"** or **"+"** button
   - Fill in the following:

   **Basic Configuration:**
   - **Name**: `pm-mcp-server`
   - **Display Name**: `Project Management MCP Server`
   - **Description**: `MCP server with 53 tools for project management (OpenProject, JIRA, ClickUp)`

   **Image Configuration:**
   - **Image**: `pm-mcp-server:latest` (local image)
   - **Tag**: `latest`

   **Transport Configuration:**
   - **Transport Type**: `SSE` (Server-Sent Events)
   - **URL**: `http://localhost:8080/sse`
   - **Port**: `8080`

   **Environment Variables:**
   Click **"Add Environment Variable"** for each:
   
   ```
   DATABASE_URL = postgresql://pm_user:pm_password@postgres:5432/project_management
   LOG_LEVEL = INFO
   ENABLE_AUTH = false
   ENABLE_RBAC = false
   MCP_TRANSPORT = sse
   MCP_HOST = 0.0.0.0
   MCP_PORT = 8080
   ```

   **Health Check:**
   - **Endpoint**: `/health`
   - **Interval**: `30` seconds
   - **Timeout**: `10` seconds
   - **Retries**: `3`

4. **Save Configuration**
   - Click **"Save"** or **"Apply"**
   - Docker Desktop will start the container

### Option B: Using Configuration File

If Docker Desktop supports configuration files, create `docker-desktop-mcp-config.json`:

```json
{
  "mcpServers": {
    "pm-mcp-server": {
      "name": "pm-mcp-server",
      "displayName": "Project Management MCP Server",
      "description": "MCP server with 53 tools for project management operations",
      "image": "pm-mcp-server:latest",
      "transport": "sse",
      "url": "http://localhost:8080/sse",
      "ports": {
        "8080": "SSE/HTTP transport"
      },
      "environment": {
        "DATABASE_URL": "postgresql://pm_user:pm_password@postgres:5432/project_management",
        "LOG_LEVEL": "INFO",
        "ENABLE_AUTH": "false",
        "ENABLE_RBAC": "false",
        "MCP_TRANSPORT": "sse",
        "MCP_HOST": "0.0.0.0",
        "MCP_PORT": "8080"
      },
      "healthCheck": {
        "endpoint": "/health",
        "interval": 30,
        "timeout": 10,
        "retries": 3
      }
    }
  }
}
```

### Option B: Use Docker Compose (Already Working!)

**Good news!** Your PM MCP Server is already running via Docker Compose and working perfectly:

```bash
# Check status
docker-compose ps pm_mcp_server

# It's already running and healthy! ✅
```

You can continue using Docker Compose - it's actually simpler and gives you more control. The MCP Toolkit UI is just a convenience feature, but Docker Compose works just as well (or better) for private/local servers.

See `docs/DOCKER_DESKTOP_MCP_ALTERNATIVE.md` for details on using Docker Compose.

## 📋 Step 5: Verify the Setup

### Check Container Status

```bash
# Check if container is running
docker ps | grep pm-mcp-server

# Check logs
docker logs pm-mcp-server
```

### Test Health Endpoint

```bash
# Test health endpoint
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "providers": 3,
  "tools": 53
}
```

### Test Tools List

```bash
# List all tools
curl -X POST http://localhost:8080/tools/list \
  -H "Content-Type: application/json" \
  -d '{}' | jq '.tools | length'
```

Should return: `53`

### Test Tool Call

```bash
# Call a tool
curl -X POST http://localhost:8080/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "list_projects",
    "arguments": {}
  }' | jq
```

## 📋 Step 6: Connect AI Clients

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pm-mcp-server": {
      "transport": "sse",
      "url": "http://localhost:8080/sse"
    }
  }
}
```

### Cursor / VS Code

Configure MCP settings to use:
- **Transport**: `sse`
- **URL**: `http://localhost:8080/sse`

## 🔧 Troubleshooting

### Container Not Starting

```bash
# Check container logs
docker logs pm-mcp-server

# Check if image exists
docker images | grep pm-mcp-server

# Rebuild if needed
docker build -f Dockerfile.mcp-server -t pm-mcp-server:latest .
```

### Database Connection Issues

```bash
# Verify database is running
docker-compose ps postgres

# Test database connection
docker exec -it pm_mcp_server python3 -c "
from database.connection import get_db_session
db = next(get_db_session())
print('✅ Database connected')
db.close()
"
```

### Port Already in Use

If port 8080 is already in use:

1. Change `MCP_PORT` environment variable to a different port (e.g., `8081`)
2. Update the URL in Docker Desktop configuration
3. Restart the container

### Health Check Failing

```bash
# Check if health endpoint is accessible
curl -v http://localhost:8080/health

# Check container health
docker inspect pm-mcp-server | grep -A 10 Health
```

## 📊 Verification Checklist

- [ ] Docker Desktop is running
- [ ] Image `pm-mcp-server:latest` exists
- [ ] Container is running (`docker ps`)
- [ ] Health endpoint returns `200 OK`
- [ ] Tools list returns 53 tools
- [ ] Can call a tool successfully
- [ ] Logs show no errors

## 🎯 Quick Reference

### Start/Stop Container

```bash
# Start (via Docker Desktop UI or)
docker start pm-mcp-server

# Stop
docker stop pm-mcp-server

# Restart
docker restart pm-mcp-server
```

### View Logs

```bash
# Follow logs
docker logs -f pm-mcp-server

# Last 100 lines
docker logs --tail 100 pm-mcp-server
```

### Update Image

```bash
# Rebuild image
docker build -f Dockerfile.mcp-server -t pm-mcp-server:latest .

# Restart container
docker restart pm-mcp-server
```

## 🚀 Next Steps

Once set up, you can:

1. **Test with AI clients**: Connect Claude Desktop, Cursor, or VS Code
2. **Use in development**: Integrate with your development workflow
3. **Share within team**: Use private registry if needed
4. **Monitor usage**: Check logs and health status regularly

## 📚 Additional Resources

- [Docker Desktop MCP Documentation](https://docs.docker.com/desktop/extensions/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [PM MCP Server Testing Guide](./PM_MCP_SERVER_TESTING_GUIDE.md)

