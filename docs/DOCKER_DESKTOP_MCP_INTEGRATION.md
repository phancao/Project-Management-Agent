# Docker Desktop MCP Toolkit Integration

## 🎯 What is Docker Desktop MCP Toolkit?

Docker Desktop's MCP Toolkit (available in Docker Desktop 4.48+) is a feature that:

- **Provides a curated catalog** of 200+ verified MCP servers
- **Enables one-click deployment** of MCP servers directly from Docker Desktop
- **Manages secure configuration** including environment variables, API keys, and credentials
- **Integrates with AI clients** like Claude, Cursor, VS Code, Windsurf, continue.dev, and Goose
- **Runs servers in isolated containers** for security

## 🚀 Benefits of Using Docker Desktop MCP Toolkit

1. **Easy Discovery**: Users can find and deploy your PM MCP Server from Docker Desktop's UI
2. **One-Click Setup**: No need to manually configure Docker Compose or environment variables
3. **Secure Configuration**: Credentials and API keys are managed securely through Docker Desktop
4. **Better Integration**: Works seamlessly with AI clients that support Docker Desktop MCP
5. **Isolated Execution**: Each MCP server runs in its own container

## 📋 Current Setup

Our PM MCP Server is already containerized and can be used with Docker Desktop's MCP Toolkit. Here's what we have:

### Current Docker Configuration

- **Dockerfile**: `Dockerfile.mcp-server`
- **Service**: `pm_mcp_server` in `docker-compose.yml`
- **Port**: 8080 (SSE/HTTP transport)
- **Health Check**: `/health` endpoint

### Current Features

✅ Containerized MCP server  
✅ SSE transport support  
✅ HTTP REST API  
✅ Health check endpoint  
✅ Database connectivity  
✅ 53 PM tools registered  

## 🔧 How to Use Docker Desktop MCP Toolkit

### Option 1: Use Existing Docker Compose Service

If you're already using `docker-compose.yml`, the PM MCP Server is available as a service:

```bash
# Start the PM MCP Server
docker-compose up -d pm_mcp_server

# Check status
docker-compose ps pm_mcp_server

# View logs
docker-compose logs -f pm_mcp_server
```

### Option 2: Deploy via Docker Desktop MCP Catalog (Future)

To make our PM MCP Server available in Docker Desktop's MCP Catalog, we need to:

1. **Create an MCP Server Manifest** (metadata file)
2. **Publish to Docker Hub or GitHub Container Registry**
3. **Submit to Docker's MCP Catalog**

## 📝 Creating MCP Server Manifest

Create a manifest file that Docker Desktop can use to discover and configure our server:

```json
{
  "name": "pm-mcp-server",
  "displayName": "Project Management MCP Server",
  "description": "MCP server providing 53 tools for project management operations across OpenProject, JIRA, ClickUp, and internal database",
  "version": "1.0.0",
  "author": "Project Management Agent",
  "repository": "https://github.com/phancao/Project-Management-Agent",
  "transport": "sse",
  "image": "project-management-agent-pm_mcp_server:latest",
  "ports": {
    "8080": "SSE/HTTP transport"
  },
  "environment": {
    "DATABASE_URL": {
      "description": "PostgreSQL database connection string",
      "required": true,
      "secret": false
    },
    "LOG_LEVEL": {
      "description": "Logging level (DEBUG, INFO, WARNING, ERROR)",
      "required": false,
      "default": "INFO"
    },
    "ENABLE_AUTH": {
      "description": "Enable authentication",
      "required": false,
      "default": "false"
    },
    "ENABLE_RBAC": {
      "description": "Enable role-based access control",
      "required": false,
      "default": "false"
    }
  },
  "healthCheck": {
    "endpoint": "/health",
    "interval": 30,
    "timeout": 10,
    "retries": 3
  },
  "tools": {
    "count": 53,
    "categories": [
      "projects",
      "tasks",
      "sprints",
      "epics",
      "users",
      "analytics",
      "task_interactions"
    ]
  }
}
```

## 🐳 Publishing to Docker Hub

To make the server available via Docker Desktop's catalog:

### 1. Build and Tag the Image

```bash
# Build the image
docker build -f Dockerfile.mcp-server -t pm-mcp-server:latest .

# Tag for Docker Hub (replace with your username)
docker tag pm-mcp-server:latest yourusername/pm-mcp-server:latest
docker tag pm-mcp-server:latest yourusername/pm-mcp-server:1.0.0
```

### 2. Push to Docker Hub

```bash
# Login to Docker Hub
docker login

# Push the image
docker push yourusername/pm-mcp-server:latest
docker push yourusername/pm-mcp-server:1.0.0
```

### 3. Create Docker Hub Repository

1. Go to [Docker Hub](https://hub.docker.com/)
2. Create a new repository: `pm-mcp-server`
3. Add description and documentation
4. Make it public (or private if preferred)

## 🔌 Configuring Docker Desktop MCP

### Manual Configuration

If you want to manually add our PM MCP Server to Docker Desktop:

1. **Open Docker Desktop**
2. **Go to Settings → Extensions → MCP**
3. **Add Custom Server**:
   - **Name**: `pm-mcp-server`
   - **Image**: `yourusername/pm-mcp-server:latest`
   - **Transport**: `sse`
   - **URL**: `http://localhost:8080/sse`
   - **Environment Variables**:
     - `DATABASE_URL`: Your PostgreSQL connection string
     - `LOG_LEVEL`: `INFO`
     - `ENABLE_AUTH`: `false`
     - `ENABLE_RBAC`: `false`

### Using Docker Compose (Current Method)

Our current setup uses Docker Compose, which works well but requires manual configuration:

```yaml
pm_mcp_server:
  build:
    context: .
    dockerfile: Dockerfile.mcp-server
  environment:
    - DATABASE_URL=postgresql://pm_user:pm_password@postgres:5432/project_management
    - LOG_LEVEL=INFO
  ports:
    - "8080:8080"
```

## 🧪 Testing with Docker Desktop MCP

### 1. Start the Server

```bash
docker-compose up -d pm_mcp_server
```

### 2. Verify Health

```bash
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

### 3. List Tools

```bash
curl -X POST http://localhost:8080/tools/list \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 4. Connect via MCP Client

If you're using an AI client that supports Docker Desktop MCP:

1. **Claude Desktop**: Add to `claude_desktop_config.json`:
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

2. **Cursor/VS Code**: Configure via MCP settings to use SSE transport

## 📊 Comparison: Docker Compose vs Docker Desktop MCP Toolkit

| Feature | Docker Compose (Current) | Docker Desktop MCP Toolkit |
|---------|-------------------------|---------------------------|
| **Setup** | Manual `docker-compose.yml` | One-click from catalog |
| **Configuration** | Manual env vars | UI-based configuration |
| **Discovery** | Manual | Catalog search |
| **Updates** | Manual pull/rebuild | Auto-update option |
| **Security** | Manual credential management | Secure credential storage |
| **Isolation** | Shared network | Isolated containers |
| **Best For** | Development, CI/CD | End users, easy setup |

## 🎯 Recommended Approach

### For Development
✅ **Use Docker Compose** (current setup)
- Full control over configuration
- Easy to modify and test
- Integrated with other services

### For End Users
✅ **Use Docker Desktop MCP Toolkit** (future)
- One-click deployment
- Secure configuration
- Better user experience

## 🚀 Next Steps

1. **Test Current Setup**: Verify the server works with Docker Compose
2. **Create Manifest**: Create MCP server manifest file
3. **Publish Image**: Push to Docker Hub
4. **Submit to Catalog**: (Optional) Submit to Docker's MCP catalog
5. **Documentation**: Update README with Docker Desktop instructions

## 📚 Resources

- [Docker MCP Toolkit Blog Post](https://www.docker.com/blog/mcp-toolkit-mcp-servers-that-just-work/)
- [Docker MCP Catalog](https://www.docker.com/products/mcp-catalog-and-toolkit/)
- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [Docker Desktop Documentation](https://docs.docker.com/desktop/)

## 🔍 Current Status

✅ **Containerized**: PM MCP Server is fully containerized  
✅ **Docker Compose**: Working with docker-compose.yml  
✅ **Health Checks**: Health endpoint implemented  
✅ **SSE Transport**: SSE transport working  
⏳ **Docker Hub**: Not yet published  
⏳ **MCP Catalog**: Not yet submitted  
⏳ **Manifest**: Not yet created  

## 💡 Quick Start

For now, the easiest way to use our PM MCP Server is via Docker Compose:

```bash
# Start the server
docker-compose up -d pm_mcp_server

# Test it
curl http://localhost:8080/health
curl -X POST http://localhost:8080/tools/list -H "Content-Type: application/json" -d '{}'

# Use with AI clients
# Configure your AI client to connect to: http://localhost:8080/sse
```

