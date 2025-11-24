# Project Management Agent - Developer Quick Reference

## 🚀 Quick Start Commands

### Initial Setup
```bash
# Clone repository
git clone <repository-url>
cd project-management-agent

# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-...

# Start all services with Docker
docker-compose up -d

# View logs
docker-compose logs -f

# Access services:
# - Frontend: http://localhost:3000
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - OpenProject v16: http://localhost:8080
# - OpenProject v13: http://localhost:8081
# - MCP Server: http://localhost:8080
```

### Local Development (Without Docker)

```bash
# Install Python dependencies
uv sync

# Start PostgreSQL and Redis
docker-compose up postgres redis -d

# Run database migrations
uv run alembic upgrade head

# Start API server
uv run uvicorn src.server:app --reload --port 8000

# In another terminal, start frontend
cd frontend
npm install
npm run dev

# In another terminal, start MCP server
python -m mcp_server.server
```

## 🔧 Common Development Tasks

### Running the Research Agent (CLI)

```bash
# Direct query
python main.py "What is quantum computing?"

# Interactive mode
python main.py --interactive

# With debug logging
python main.py "Research topic" --debug

# Disable background investigation
python main.py "Query" --no-background-investigation

# Enable clarification
python main.py "Vague query" --enable-clarification

# Custom parameters
python main.py "Query" --max-plan-iterations 3 --max-step-num 5
```

### Working with PM Providers

```bash
# Test OpenProject connection
python scripts/tests/test_openproject_connection.py

# List all projects
python scripts/utils/list_projects.py

# Create a test project
python scripts/utils/create_test_project.py

# Sync with external PM system
python scripts/utils/sync_provider.py
```

### Database Operations

```bash
# Create migration
uv run alembic revision --autogenerate -m "Description"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Reset database
docker-compose down -v
docker-compose up postgres -d
uv run alembic upgrade head

# Connect to database
psql -h localhost -U pm_user -d project_management

# Seed test data
psql -h localhost -U pm_user -d project_management -f database/seed_providers.sql
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=backend --cov=mcp_server --cov=pm_providers

# Run specific test file
uv run pytest tests/test_pm_features.py

# Run specific test
uv run pytest tests/test_pm_features.py::test_create_project

# Run with verbose output
uv run pytest -v

# Run frontend tests
cd frontend
npm test

# Run frontend tests with coverage
npm run test:coverage
```

### Linting and Formatting

```bash
# Format code with Ruff
uv run ruff format .

# Lint code
uv run ruff check .

# Fix linting issues
uv run ruff check --fix .

# Format frontend code
cd frontend
npm run format

# Lint frontend code
npm run lint
```

## 📝 Code Snippets

### Creating a New PM Provider

```python
# pm_providers/my_provider.py
from typing import List, Optional
from .base import BasePMProvider
from .models import PMProject, PMTask, PMSprint, PMUser

class MyProvider(BasePMProvider):
    """Custom PM provider implementation."""
    
    def __init__(self, config: dict):
        self.base_url = config.get("base_url")
        self.api_key = config.get("api_key")
        # Initialize your client
    
    async def list_projects(self) -> List[PMProject]:
        """List all projects."""
        # Call your API
        response = await self.client.get("/projects")
        # Transform to PMProject
        return [self._to_pm_project(p) for p in response]
    
    async def create_task(self, task: PMTask) -> PMTask:
        """Create a new task."""
        # Transform PMTask to your API format
        data = self._from_pm_task(task)
        # Call your API
        response = await self.client.post("/tasks", json=data)
        # Transform response back to PMTask
        return self._to_pm_task(response)
    
    # Implement other required methods...
```

### Adding a New API Endpoint

```python
# src/server/app.py or backend/server/app.py
from fastapi import APIRouter, Depends, HTTPException
from database import get_db_session
from pm_providers import build_pm_provider

router = APIRouter(prefix="/api/custom", tags=["custom"])

@router.get("/my-endpoint")
async def my_endpoint(
    db: Session = Depends(get_db_session)
):
    """Custom endpoint description."""
    try:
        provider = build_pm_provider(db_session=db)
        result = await provider.some_operation()
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Register router in app.py
app.include_router(router)
```

### Creating a New MCP Tool

```python
# mcp_server/tools/my_tool.py
from mcp.types import Tool, TextContent
from typing import Any

async def my_tool_handler(arguments: dict[str, Any], context: dict) -> list[TextContent]:
    """
    Custom tool handler.
    
    Args:
        arguments: Tool arguments from the agent
        context: Request context (user, db, etc.)
    
    Returns:
        List of text content responses
    """
    # Extract arguments
    param1 = arguments.get("param1")
    param2 = arguments.get("param2")
    
    # Get dependencies from context
    pm_handler = context.get("pm_handler")
    
    # Perform operation
    result = await pm_handler.some_operation(param1, param2)
    
    # Return formatted response
    return [
        TextContent(
            type="text",
            text=f"Operation completed: {result}"
        )
    ]

# Tool definition
MY_TOOL = Tool(
    name="my_tool",
    description="Description of what this tool does",
    inputSchema={
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "Description of param1"
            },
            "param2": {
                "type": "number",
                "description": "Description of param2"
            }
        },
        "required": ["param1"]
    }
)

# Register in mcp_server/server.py
from .tools.my_tool import MY_TOOL, my_tool_handler
server.register_tool(MY_TOOL, my_tool_handler)
```

### Creating a Frontend Component

```typescript
// web/src/components/MyComponent.tsx
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

interface MyComponentProps {
  projectId: string;
}

export function MyComponent({ projectId }: MyComponentProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['my-data', projectId],
    queryFn: () => apiClient.get(`/api/projects/${projectId}/data`),
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold">{data.title}</h2>
      <p>{data.description}</p>
    </div>
  );
}
```

### Using the PM Provider in Code

```python
# In any handler or service
from database import get_db_session
from pm_providers import build_pm_provider
from pm_providers.models import PMTask

async def create_task_example():
    # Get database session
    db = next(get_db_session())
    
    # Build provider (automatically uses configured provider)
    provider = build_pm_provider(db_session=db)
    
    # Create a task
    new_task = PMTask(
        id="",  # Will be generated
        title="Implement new feature",
        description="Add support for custom fields",
        status="open",
        priority="high",
        project_id="project-123",
        estimated_hours=8.0
    )
    
    # Provider handles the rest (internal DB or external API)
    created_task = await provider.create_task(new_task)
    
    print(f"Task created: {created_task.id}")
    return created_task
```

## 🐛 Debugging

### Enable Debug Logging

```bash
# For API server
python server.py --log-level debug

# For research agent
python main.py "Query" --debug

# For MCP server
export LOG_LEVEL=DEBUG
python -m mcp_server.server

# Smart debug configuration (environment variables)
export DEBUG_PM_PROVIDER=true
export DEBUG_MCP_CLIENT=true
export DEBUG_AGENT_WORKFLOW=true
python server.py
```

### Debug in VSCode

Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "src.server:app",
        "--reload",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false
    },
    {
      "name": "Python: Research Agent",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/main.py",
      "args": ["What is AI?", "--debug"],
      "console": "integratedTerminal"
    }
  ]
}
```

### Common Debug Scenarios

```python
# Debug PM provider selection
import logging
logging.basicConfig(level=logging.DEBUG)

from pm_providers import build_pm_provider
provider = build_pm_provider(db_session=db)
# Will log: "Using provider: openproject" or "Using provider: internal"

# Debug MCP tool calls
# In mcp_server/server.py, add logging:
logger.debug(f"Tool called: {tool_name}, args: {arguments}")

# Debug agent workflow
# In src/workflow.py, enable debug mode:
from src.workflow import run_agent_workflow_async
await run_agent_workflow_async(
    user_input="Query",
    debug=True  # Enables detailed logging
)
```

## 🔍 Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check connection
psql -h localhost -U pm_user -d project_management -c "SELECT 1"

# Reset database
docker-compose down postgres
docker-compose up -d postgres
sleep 5
uv run alembic upgrade head
```

### MCP Server Issues

```bash
# Check MCP server health
curl http://localhost:8080/health

# Check MCP server logs
docker-compose logs pm_mcp_server

# Test MCP connection
python scripts/tests/test_mcp_connection.py

# Restart MCP server
docker-compose restart pm_mcp_server
```

### OpenProject Connection Issues

```bash
# Check OpenProject is running
curl http://localhost:8080/api/v3/status

# Test OpenProject API
export OPENPROJECT_URL=http://localhost:8080
export OPENPROJECT_API_KEY=your-api-key
python scripts/tests/test_openproject_connection.py

# View OpenProject logs
docker-compose logs openproject
```

### Frontend Build Issues

```bash
# Clear Next.js cache
cd frontend
rm -rf .next
npm run build

# Clear node_modules
rm -rf node_modules
npm install

# Check for TypeScript errors
npm run type-check
```

## 📊 Monitoring

### Check Service Health

```bash
# API health
curl http://localhost:8000/health

# MCP server health
curl http://localhost:8080/health

# Database health
docker-compose exec postgres pg_isready -U pm_user

# Redis health
docker-compose exec redis redis-cli ping
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f pm_mcp_server
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100 api
```

### Database Queries

```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'project_management';

-- List all projects
SELECT id, name, status FROM projects;

-- List all tasks
SELECT id, title, status, project_id FROM tasks;

-- Check PM provider connections
SELECT * FROM pm_provider_connections;

-- Check API keys
SELECT id, name, user_id, expires_at FROM api_keys;
```

## 🔐 Environment Variables Reference

### Required
```bash
OPENAI_API_KEY=sk-...                    # OpenAI API key
DATABASE_URL=postgresql://...            # Main database
```

### Optional
```bash
# PM Provider Configuration
PM_PROVIDER=internal                     # internal|openproject|jira|clickup
OPENPROJECT_URL=http://localhost:8080
OPENPROJECT_API_KEY=your-key

# MCP Server
PM_MCP_SERVER_URL=http://localhost:8080/sse
PM_MCP_TRANSPORT=sse                     # sse|http|stdio
PM_MCP_API_KEY=your-key

# Redis
REDIS_URL=redis://localhost:6379

# Environment
ENVIRONMENT=development                   # development|production
LOG_LEVEL=INFO                           # DEBUG|INFO|WARNING|ERROR

# Debug Flags
DEBUG_PM_PROVIDER=false
DEBUG_MCP_CLIENT=false
DEBUG_AGENT_WORKFLOW=false
```

## 📚 Useful Resources

### API Documentation
- FastAPI Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenProject API: https://www.openproject.org/docs/api/

### Internal Documentation
- Main README: [README.md](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/README.md)
- PM Providers: [pm_providers/README.md](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/pm_providers/README.md)
- MCP Server: [mcp_server/README.md](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/mcp_server/README.md)

### Key Files
- Workflow: [src/workflow.py](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/src/workflow.py)
- Main API: [src/server/app.py](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/src/server/app.py)
- Database Schema: [database/schema.sql](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/database/schema.sql)

## 🎯 Common Workflows

### Adding a New Feature

1. **Plan**: Document in `docs/`
2. **Database**: Create migration if needed
3. **Backend**: Add API endpoint
4. **Provider**: Update PM provider if needed
5. **Frontend**: Add UI component
6. **Test**: Write tests
7. **Document**: Update README

### Debugging a Bug

1. **Reproduce**: Create minimal test case
2. **Logs**: Check relevant service logs
3. **Debug**: Use VSCode debugger or print statements
4. **Fix**: Implement fix
5. **Test**: Verify fix works
6. **Prevent**: Add test to prevent regression

### Deploying Changes

1. **Test locally**: `docker-compose up`
2. **Run tests**: `uv run pytest`
3. **Build**: `docker-compose build`
4. **Deploy**: Push to production
5. **Monitor**: Check logs and health endpoints

---

**Last Updated**: 2025-11-22
**Quick Tip**: Bookmark this page for fast reference!
