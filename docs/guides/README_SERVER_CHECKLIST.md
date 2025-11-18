# Server Checklist

Before testing or using the Project Management Agent, ensure all required services are running.

## Quick Check

Run the server checklist script to verify all services:

```bash
./scripts/check_servers.sh
```

This will check:
- ✅ OpenProject service (port 8080)
- ✅ Frontend server (port 3000)
- ✅ Backend server (port 8000)
- ✅ PostgreSQL database (port 5432)
- ✅ Other optional services (Redis, etc.)

## Required Services

### 1. OpenProject
- **Port**: 8080
- **URL**: http://localhost:8080
- **Start**: `docker-compose up -d openproject_db openproject`

### 2. Frontend
- **Port**: 3000
- **URL**: http://localhost:3000
- **Start**: `cd web && npm run dev`

### 3. Backend
- **Port**: 8000
- **URL**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Start**: `uv run python server.py --host localhost --port 8000`

### 4. PostgreSQL Database
- **Port**: 5432
- **Start**: `docker-compose up -d postgres`

## Quick Start All Services

To start all services at once:

```bash
./scripts/start_all_servers.sh
```

This script will:
1. Start all Docker services (OpenProject, PostgreSQL)
2. Start the backend server
3. Start the frontend server
4. Run the checklist to verify everything is ready

## Manual Service Management

### Start Individual Services

**Docker Services:**
```bash
docker-compose up -d
```

**Backend:**
```bash
uv run python server.py --host localhost --port 8000 --log-level info
```

**Frontend:**
```bash
cd web
npm run dev
```

### Stop Services

**Stop all Docker services:**
```bash
docker-compose down
```

**Stop backend (if running as background process):**
```bash
kill $(cat /tmp/deerflow_server.pid) 2>/dev/null || pkill -f "python.*server.py"
```

**Stop frontend (if running as background process):**
```bash
kill $(cat /tmp/frontend_server.pid) 2>/dev/null || pkill -f "next.*dev"
```

## Service Status

### Check Service Logs

**Backend logs:**
```bash
tail -f /tmp/deerflow_server.log
```

**Frontend logs:**
```bash
tail -f /tmp/frontend_server.log
```

**Docker service logs:**
```bash
docker-compose logs -f [service_name]
```

### Verify Services Manually

**Check OpenProject:**
```bash
curl http://localhost:8080
```

**Check Frontend:**
```bash
curl http://localhost:3000
```

**Check Backend:**
```bash
curl http://localhost:8000/docs
```

**Check PostgreSQL:**
```bash
nc -z localhost 5432 && echo "PostgreSQL is running"
```

## Troubleshooting

### Service Not Starting

1. **Check if ports are already in use:**
   ```bash
   lsof -i :8080  # OpenProject
   lsof -i :3000  # Frontend
   lsof -i :8000  # Backend
   lsof -i :5432  # PostgreSQL
   ```

2. **Check Docker containers:**
   ```bash
   docker ps -a
   docker logs [container_name]
   ```

3. **Check service logs:**
   - Backend: `/tmp/deerflow_server.log`
   - Frontend: `/tmp/frontend_server.log`
   - Docker: `docker-compose logs`

### Common Issues

**OpenProject takes time to start:**
- OpenProject can take 2-5 minutes to fully initialize
- Wait for health check to pass: `docker ps | grep openproject`

**Backend fails to start:**
- Ensure dependencies are installed: `uv sync`
- Check database connection in `.env`

**Frontend fails to start:**
- Ensure dependencies are installed: `cd web && npm install`
- Check if port 3000 is available

## Testing Workflow

1. **Before testing, always run:**
   ```bash
   ./scripts/check_servers.sh
   ```

2. **Only proceed if all services show ✅**

3. **If any service is missing:**
   ```bash
   ./scripts/start_all_servers.sh
   ```

4. **Then run the checklist again to verify**
