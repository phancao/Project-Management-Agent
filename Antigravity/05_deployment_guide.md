# Deployment Guide

> **Last Updated**: November 25, 2025

## 🚀 Quick Start (Docker Compose)

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum
- 20GB disk space

### 1. Clone Repository

```bash
git clone <repository-url>
cd Project-Management-Agent
```

### 2. Configure Environment

Create `.env` file:

```bash
# Copy example
cp .env.example .env

# Edit with your values
nano .env
```

**Required Environment Variables**:

```bash
# OpenAI API Key (REQUIRED)
OPENAI_API_KEY=sk-your-openai-api-key

# Database (auto-configured in Docker)
DATABASE_URL=postgresql://pm_user:pm_password@postgres:5432/project_management

# MCP Server (auto-configured)
PM_MCP_SERVER_URL=http://pm_mcp_server:8080/sse
PM_MCP_API_KEY=mcp_a9b43d595b627e1e094209dea14bcb32f98867649ae181d4836dde87e283ccc3

# Search Engine (optional, defaults to DuckDuckGo)
SEARCH_API=duckduckgo
# TAVILY_API_KEY=your-tavily-key  # If using Tavily

# OpenProject (optional, for testing)
OPENPROJECT_SECRET_KEY=your-secret-key-change-in-production
OPENPROJECT_SECRET_KEY_V13=your-secret-key-v13-change-in-production
```

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 4. Access Applications

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **OpenProject v16**: http://localhost:8082
- **OpenProject v13**: http://localhost:8083
- **MCP Server**: http://localhost:8080

### 5. Initial Setup

#### Create OpenProject API Key

1. Access OpenProject: http://localhost:8082
2. Login (default: admin/admin)
3. Go to: My Account → Access Tokens
4. Create new token with full permissions
5. Copy token to `.env`:

```bash
OPENPROJECT_API_KEY=your-token-here
```

#### Configure PM Provider

```bash
# Restart backend to pick up new API key
docker-compose restart api
```

## 🏗️ Service Architecture

### Docker Services

```mermaid
graph TB
    subgraph "Frontend"
        FE[Next.js:3000]
    end
    
    subgraph "Backend"
        API[FastAPI:8000]
        MCP[MCP Server:8080]
    end
    
    subgraph "Databases"
        PG[(PostgreSQL:5432)]
        MCPDB[(MCP DB:5435)]
        Redis[(Redis:6379)]
        Qdrant[(Qdrant:6333)]
    end
    
    subgraph "PM Systems"
        OP16[OpenProject v16:8082]
        OP13[OpenProject v13:8083]
        OPDB16[(OP DB:5433)]
        OPDB13[(OP DB:5434)]
    end
    
    FE --> API
    API --> PG
    API --> Redis
    API --> Qdrant
    API --> MCP
    MCP --> MCPDB
    MCP --> OP16
    MCP --> OP13
    OP16 --> OPDB16
    OP13 --> OPDB13
```

### Port Mapping

| Service | Internal Port | External Port | Purpose |
|---------|--------------|---------------|---------|
| Frontend | 3000 | 3000 | Web UI |
| Backend API | 8000 | 8000 | REST API |
| MCP Server | 8080 | 8080 | MCP Protocol |
| PostgreSQL | 5432 | 5432 | Main DB |
| Redis | 6379 | 6379 | Cache |
| Qdrant | 6333 | 6333 | Vector DB |
| OpenProject v16 | 80 | 8082 | PM System |
| OpenProject v13 | 80 | 8083 | PM System (legacy) |
| OP DB v16 | 5432 | 5433 | OP Database |
| OP DB v13 | 5432 | 5434 | OP Database |
| MCP DB | 5432 | 5435 | MCP Database |

### Volume Mapping

```yaml
volumes:
  postgres_data:           # Main database data
  mcp_postgres_data:       # MCP server database
  qdrant_data:             # Vector database
  openproject_db_data:     # OpenProject v16 DB
  openproject_data:        # OpenProject v16 assets
  openproject_db_data_v13: # OpenProject v13 DB
  openproject_data_v13:    # OpenProject v13 assets
```

## 🔧 Configuration Files

### docker-compose.yml

Key configurations:

```yaml
services:
  api:
    environment:
      - DATABASE_URL=postgresql://pm_user:pm_password@postgres:5432/project_management
      - PM_MCP_SERVER_URL=http://pm_mcp_server:8080/sse
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      pm_mcp_server:
        condition: service_healthy

  pm_mcp_server:
    environment:
      - DATABASE_URL=postgresql://mcp_user:mcp_password@mcp-postgres:5432/mcp_server
      - MCP_TRANSPORT=sse
    ports:
      - "8080:8080"
```

### conf.yaml

LLM and tool configurations:

```yaml
BASIC_MODEL:
  base_url: "https://api.openai.com/v1"
  model: "gpt-4o-mini"
  api_key: "${OPENAI_API_KEY}"

REASONING_MODEL:
  model: "o1-mini"
  api_key: "${OPENAI_API_KEY}"

SEARCH_ENGINE:
  engine: duckduckgo
  max_results: 5

RAG:
  provider: milvus
  collection_name: "research_docs"
```

## 📊 Health Checks

All services have health checks configured:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Check Service Health

```bash
# Check all services
docker-compose ps

# Check specific service logs
docker-compose logs api
docker-compose logs pm_mcp_server

# Check health endpoint
curl http://localhost:8000/health
curl http://localhost:8080/health
```

## 🔄 Common Operations

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart api
docker-compose restart pm_mcp_server
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f pm_mcp_server

# Last 100 lines
docker-compose logs --tail=100 api
```

### Update Code

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose up -d --build

# Or rebuild specific service
docker-compose up -d --build api
```

### Database Operations

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U pm_user -d project_management

# Backup database
docker-compose exec postgres pg_dump -U pm_user project_management > backup.sql

# Restore database
docker-compose exec -T postgres psql -U pm_user project_management < backup.sql

# Access MCP database
docker-compose exec mcp_postgres psql -U mcp_user -d mcp_server
```

### Clean Up

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs service_name

# Check if port is in use
lsof -i :8000  # Check port 8000
lsof -i :3000  # Check port 3000

# Restart service
docker-compose restart service_name
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection
docker-compose exec api python -c "from sqlalchemy import create_engine; engine = create_engine('postgresql://pm_user:pm_password@postgres:5432/project_management'); print(engine.connect())"
```

### MCP Server Issues

```bash
# Check MCP server logs
docker-compose logs pm_mcp_server

# Test MCP health
curl http://localhost:8080/health

# Restart MCP server
docker-compose restart pm_mcp_server
```

### OpenProject Issues

```bash
# Check OpenProject logs
docker-compose logs openproject

# Access OpenProject container
docker-compose exec openproject bash

# Reset OpenProject admin password
docker-compose exec openproject bundle exec rails runner "User.admin.first.update(password: 'newpassword', password_confirmation: 'newpassword')"
```

## 🔒 Security Considerations

### Production Deployment

1. **Change Default Passwords**:
```bash
# PostgreSQL
POSTGRES_PASSWORD=strong-random-password

# OpenProject
OPENPROJECT_SECRET_KEY=strong-random-key
```

2. **Use HTTPS**:
```yaml
# Add nginx reverse proxy
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
```

3. **Enable MCP Authentication**:
```yaml
pm_mcp_server:
  environment:
    - ENABLE_AUTH=true
    - ENABLE_RBAC=true
```

4. **Restrict Network Access**:
```yaml
# Only expose necessary ports
ports:
  - "127.0.0.1:8000:8000"  # API only on localhost
  - "443:443"              # HTTPS only
```

## 📈 Monitoring

### Prometheus + Grafana (Optional)

```yaml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
    depends_on:
      - prometheus
```

### Log Aggregation

```bash
# Use Docker logging driver
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

**Next**: [Developer Guide →](./06_developer_guide.md)
