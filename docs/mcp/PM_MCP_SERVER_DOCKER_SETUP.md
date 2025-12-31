# PM MCP Server Docker Setup

This document describes how to run the PM MCP Server as a dedicated Docker service.

## Benefits of Docker Deployment

1. **Isolation**: MCP server failures don't affect the main application
2. **Scalability**: Scale MCP server independently based on load
3. **Resource Management**: Dedicated CPU/memory allocation
4. **Independent Deployment**: Update MCP server without restarting main app
5. **Production Ready**: Follows microservices best practices
6. **Multi-Instance**: Run multiple instances for load balancing

## Quick Start

### Using Docker Compose

```bash
# Start all services including MCP server
docker-compose up -d pm_mcp_server

# View logs
docker-compose logs -f pm_mcp_server

# Stop MCP server
docker-compose stop pm_mcp_server
```

### Standalone Docker

```bash
# Build the image
docker build -f Dockerfile.mcp-server -t pm-mcp-server:latest .

# Run with SSE transport (recommended for Docker)
docker run -d \
  --name pm-mcp-server \
  -p 8080:8080 \
  -e DATABASE_URL=postgresql://pm_user:pm_password@host.docker.internal:5432/project_management \
  -e MCP_TRANSPORT=sse \
  pm-mcp-server:latest
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | Required | PostgreSQL connection string |
| `MCP_TRANSPORT` | `sse` | Transport type: `sse`, `http`, or `stdio` |
| `MCP_HOST` | `0.0.0.0` | Host to bind to (for SSE/HTTP) |
| `MCP_PORT` | `8080` | Port to bind to (for SSE/HTTP) |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ENABLE_AUTH` | `false` | Enable authentication |
| `ENABLE_RBAC` | `false` | Enable role-based access control |

### Transport Types

#### SSE (Server-Sent Events) - Recommended for Docker
- Best for web-based agents
- HTTP-based, easy to load balance
- Real-time streaming support
- URL: `http://pm_mcp_server:8080/sse`

#### HTTP (RESTful)
- Standard REST API
- Good for simple integrations
- URL: `http://pm_mcp_server:8080/mcp`

#### stdio (Standard I/O)
- For process-based clients (e.g., Claude Desktop)
- Not recommended for Docker (use SSE/HTTP instead)
- Requires process management

## Integration with Main Application

### Update MCP Configuration

In your main application's MCP settings, use the Docker service URL:

```json
{
  "mcp_settings": {
    "servers": {
      "pm-server": {
        "transport": "sse",
        "url": "http://pm_mcp_server:8080/sse",
        "headers": {
          "Authorization": "Bearer YOUR_TOKEN"  // If auth enabled
        },
        "enabled_tools": ["list_projects", "get_project", "create_project"],
        "add_to_agents": ["researcher", "coder"]
      }
    }
  }
}
```

### For External Access

If accessing from outside Docker network:

```json
{
  "transport": "sse",
  "url": "http://localhost:8080/sse"
}
```

## Health Checks

The MCP server includes a health check endpoint:

```bash
# Check health
curl http://localhost:8080/health

# Expected response
{"status": "healthy", "version": "0.1.0"}
```

Docker Compose automatically monitors health and restarts if unhealthy.

## Scaling

### Scale Horizontally

```bash
# Run multiple instances
docker-compose up -d --scale pm_mcp_server=3

# Use load balancer (nginx example)
upstream mcp_servers {
    least_conn;
    server pm_mcp_server_1:8080;
    server pm_mcp_server_2:8080;
    server pm_mcp_server_3:8080;
}
```

### Resource Limits

Adjust in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # Max CPU
      memory: 1G       # Max memory
    reservations:
      cpus: '1.0'      # Guaranteed CPU
      memory: 512M     # Guaranteed memory
```

## Monitoring

### Logs

```bash
# View logs
docker-compose logs -f pm_mcp_server

# View last 100 lines
docker-compose logs --tail=100 pm_mcp_server

# Export logs
docker-compose logs pm_mcp_server > mcp_server.log
```

### Metrics

The server logs include:
- Request counts
- Response times
- Error rates
- Tool usage statistics

## Troubleshooting

### Server Not Starting

1. Check database connection:
   ```bash
   docker-compose exec pm_mcp_server uv run python -c "from database.connection import get_db_session; next(get_db_session())"
   ```

2. Check logs:
   ```bash
   docker-compose logs pm_mcp_server
   ```

3. Verify environment variables:
   ```bash
   docker-compose exec pm_mcp_server env | grep MCP
   ```

### Connection Issues

1. Verify network connectivity:
   ```bash
   docker-compose exec api curl http://pm_mcp_server:8080/health
   ```

2. Check firewall/ports:
   ```bash
   docker-compose ps pm_mcp_server
   ```

### Performance Issues

1. Monitor resource usage:
   ```bash
   docker stats pm_mcp_server
   ```

2. Adjust resource limits in `docker-compose.yml`

3. Scale horizontally if needed

## Production Recommendations

1. **Use SSE Transport**: Best for Docker deployments
2. **Enable Authentication**: Set `ENABLE_AUTH=true` in production
3. **Enable RBAC**: Set `ENABLE_RBAC=true` for fine-grained access control
4. **Use Secrets**: Store sensitive data in Docker secrets or environment files
5. **Set Resource Limits**: Prevent resource exhaustion
6. **Enable Health Checks**: Automatic restart on failure
7. **Use Load Balancer**: For multiple instances
8. **Monitor Logs**: Set up log aggregation (e.g., ELK stack)
9. **Backup Database**: Regular backups of PM data
10. **Update Regularly**: Keep MCP server updated

## Migration from Standalone

If you're currently running the MCP server standalone:

1. **Stop standalone server**:
   ```bash
   # If running as process
   pkill -f run_pm_mcp_server.py
   ```

2. **Update MCP configuration** to use Docker service URL

3. **Start Docker service**:
   ```bash
   docker-compose up -d pm_mcp_server
   ```

4. **Verify connection**:
   ```bash
   curl http://localhost:8080/health
   ```

## Development

For development, you can still run locally:

```bash
# Local development (not in Docker)
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080
```

The Docker setup is primarily for production deployments.

