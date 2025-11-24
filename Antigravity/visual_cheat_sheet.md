# 🎨 Project Management Agent - Visual Cheat Sheet

## 📁 File Location Quick Map

```
Project-Management-Agent/
│
├── 🚀 ENTRY POINTS
│   ├── main.py                    # CLI research mode
│   ├── server.py                  # API server startup
│   └── docker-compose.yml         # Full stack orchestration
│
├── ⚙️ CONFIGURATION
│   ├── .env                       # Environment variables (create from .env.example)
│   ├── conf.yaml                  # Runtime config (LLM settings)
│   ├── pyproject.toml             # Python dependencies
│   └── langgraph.json             # LangGraph config
│
├── 🗄️ DATABASE
│   └── database/
│       ├── schema.sql             # Main database schema
│       ├── mcp_server_schema.sql  # MCP server schema
│       ├── models.py              # Pydantic models
│       └── orm_models.py          # SQLAlchemy ORM models
│
├── 🔧 BACKEND
│   ├── src/                       # Main source code
│   │   ├── server/app.py          # FastAPI application (151KB!)
│   │   ├── workflow.py            # Agent workflow orchestration
│   │   ├── agents/                # Agent implementations
│   │   ├── graph/                 # LangGraph workflows
│   │   ├── tools/                 # Agent tools
│   │   └── prompts/               # LLM prompts
│   │
│   ├── pm_providers/              # PM provider abstraction
│   │   ├── base.py                # Base interface
│   │   ├── internal.py            # Internal DB provider
│   │   ├── openproject.py         # OpenProject provider
│   │   ├── jira.py                # JIRA provider (stub)
│   │   └── clickup.py             # ClickUp provider (stub)
│   │
│   └── mcp_server/                # MCP server
│       ├── server.py              # MCP server implementation
│       ├── pm_handler.py          # PM operations handler
│       └── tools/                 # MCP tools
│
├── 🎨 FRONTEND
│   └── web/ (or frontend/)
│       ├── src/
│       │   ├── app/               # Next.js pages
│       │   ├── components/        # React components
│       │   ├── hooks/             # Custom hooks
│       │   └── lib/               # Utilities
│       └── public/                # Static assets
│
├── 🧪 TESTING
│   ├── tests/                     # Official test suite (pytest)
│   └── scripts/tests/             # Standalone test scripts
│
└── 📚 DOCUMENTATION
    ├── README.md                  # Main documentation
    ├── docs/                      # Additional docs
    └── .gemini/antigravity/brain/ # Learning materials
        ├── codebase_overview.md
        ├── architecture_deep_dive.md
        ├── developer_quick_reference.md
        └── learning_guide.md
```

## 🔄 Data Flow Cheat Sheet

### UI Operation (Fast Path)
```
User Click → Frontend → REST API → PMHandler → Provider → Database/External API
                                                              ↓
                                                          Response
```
**Speed**: 10-50ms | **Use**: CRUD operations, page loads

### Conversational Query (Smart Path)
```
User Message → Frontend → Chat API → DeerFlow Agent → MCP Server → PMHandler → Provider
                                           ↓
                                      LLM Reasoning
                                           ↓
                                      Tool Calls
                                           ↓
                                      Response
```
**Speed**: 100-500ms | **Use**: Natural language queries, complex operations

## 🎯 Service Ports Quick Reference

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| Frontend | 3000 | http://localhost:3000 | Next.js UI |
| API | 8000 | http://localhost:8000 | FastAPI backend |
| API Docs | 8000 | http://localhost:8000/docs | Swagger UI |
| MCP Server | 8080 | http://localhost:8080 | MCP protocol |
| OpenProject v16 | 8080 | http://localhost:8080 | PM system |
| OpenProject v13 | 8081 | http://localhost:8081 | PM system (legacy) |
| PostgreSQL (main) | 5432 | localhost:5432 | Main database |
| PostgreSQL (MCP) | 5435 | localhost:5435 | MCP database |
| PostgreSQL (OP v16) | 5433 | localhost:5433 | OpenProject DB |
| PostgreSQL (OP v13) | 5434 | localhost:5434 | OpenProject DB v13 |
| Qdrant | 6333 | http://localhost:6333 | Vector database |
| Redis | 6379 | localhost:6379 | Cache |

## 🚀 Command Cheat Sheet

### Docker Operations
```bash
# Start everything
docker-compose up -d

# Start specific service
docker-compose up -d postgres redis

# View logs
docker-compose logs -f api

# Restart service
docker-compose restart api

# Stop everything
docker-compose down

# Stop and remove volumes (DANGER: deletes data)
docker-compose down -v

# Rebuild images
docker-compose build

# Check status
docker-compose ps
```

### Development
```bash
# Install dependencies
uv sync

# Run API server
uv run uvicorn src.server:app --reload --port 8000

# Run research agent
python main.py "Your query"
python main.py --interactive

# Run with debug
python main.py "Query" --debug
python server.py --log-level debug

# Run MCP server
python -m mcp_server.server
```

### Database
```bash
# Create migration
uv run alembic revision --autogenerate -m "Description"

# Apply migrations
uv run alembic upgrade head

# Rollback
uv run alembic downgrade -1

# Connect to DB
psql -h localhost -U pm_user -d project_management
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test
uv run pytest tests/test_file.py::test_function

# Frontend tests
cd frontend && npm test
```

### Code Quality
```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Fix linting issues
uv run ruff check --fix .
```

## 🗄️ Database Quick Reference

### Main Database Tables
```
users              → User accounts
projects           → Project information
tasks              → Task details
sprints            → Sprint data
team_members       → Team assignments
research_sessions  → Research history
knowledge_base     → Vector-stored knowledge
conversation_sessions → Chat sessions
project_metrics    → Analytics
```

### MCP Database Tables
```
users                      → MCP server users
api_keys                   → API key management
pm_provider_connections    → External PM connections
project_sync_mappings      → Sync mappings
```

### Common Queries
```sql
-- List all projects
SELECT id, name, status FROM projects;

-- List tasks for a project
SELECT id, title, status FROM tasks WHERE project_id = 'xxx';

-- Check active sprints
SELECT * FROM sprints WHERE status = 'active';

-- List team members
SELECT u.username, tm.role 
FROM team_members tm 
JOIN users u ON tm.user_id = u.id 
WHERE tm.project_id = 'xxx';
```

## 🔑 Environment Variables Quick Reference

### Required
```bash
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://pm_user:pm_password@localhost:5432/project_management
```

### PM Provider
```bash
PM_PROVIDER=internal                    # internal|openproject|jira|clickup
OPENPROJECT_URL=http://localhost:8080
OPENPROJECT_API_KEY=your-key
```

### MCP Server
```bash
PM_MCP_SERVER_URL=http://localhost:8080/sse
PM_MCP_TRANSPORT=sse                    # sse|http|stdio
PM_MCP_API_KEY=your-key
```

### Optional
```bash
REDIS_URL=redis://localhost:6379
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG_PM_PROVIDER=false
DEBUG_MCP_CLIENT=false
```

## 🎨 Architecture Patterns Quick Reference

### Factory Pattern (PM Providers)
```python
# Automatically creates the right provider
provider = build_pm_provider(db_session=db)
# Returns: InternalProvider | OpenProjectProvider | etc.
```

### Strategy Pattern (MCP Transports)
```python
# Different transport strategies
transport = SSETransport()      # Server-Sent Events
transport = HTTPTransport()     # HTTP polling
transport = StdioTransport()    # Standard I/O
```

### Adapter Pattern (Provider Interface)
```python
# Each provider adapts to common interface
class OpenProjectProvider(BasePMProvider):
    async def create_task(self, task: PMTask) -> PMTask:
        # Adapt PMTask → OpenProject format
        # Call OpenProject API
        # Adapt response → PMTask
```

## 🔍 Debugging Quick Guide

### Enable Debug Logging
```bash
# API server
python server.py --log-level debug

# Research agent
python main.py "Query" --debug

# MCP server
export LOG_LEVEL=DEBUG
python -m mcp_server.server

# Smart debug (environment)
export DEBUG_PM_PROVIDER=true
export DEBUG_MCP_CLIENT=true
```

### Check Service Health
```bash
# API
curl http://localhost:8000/health

# MCP Server
curl http://localhost:8080/health

# Database
docker-compose exec postgres pg_isready -U pm_user

# Redis
docker-compose exec redis redis-cli ping
```

### Common Issues
```bash
# Database connection failed
→ Check: docker-compose ps postgres
→ Fix: docker-compose restart postgres

# MCP server not responding
→ Check: docker-compose logs pm_mcp_server
→ Fix: docker-compose restart pm_mcp_server

# Frontend build error
→ Check: cd frontend && npm run type-check
→ Fix: rm -rf .next && npm run build

# Port already in use
→ Check: lsof -i :8000
→ Fix: kill -9 <PID> or change port
```

## 📊 Technology Stack at a Glance

### Backend
```
Python 3.12+ ────┬──→ FastAPI (API framework)
                 ├──→ LangChain (LLM framework)
                 ├──→ LangGraph (Agent workflows)
                 ├──→ SQLAlchemy (ORM)
                 ├──→ Pydantic (Validation)
                 └──→ Alembic (Migrations)
```

### Frontend
```
TypeScript ──────┬──→ Next.js 14 (React framework)
                 ├──→ Tailwind CSS (Styling)
                 ├──→ React Query (Data fetching)
                 └──→ OpenAI ChatKit (Chat UI)
```

### Data Layer
```
PostgreSQL ──────┬──→ Main database (projects, tasks)
                 └──→ MCP database (auth, connections)

Qdrant ──────────┬──→ Vector database (embeddings)

Redis ───────────┬──→ Cache & sessions
```

### AI/ML
```
OpenAI ──────────┬──→ GPT-4o-mini (LLM)
                 └──→ Embeddings (Vector search)

DeerFlow ────────┬──→ Research framework
```

## 🎯 Common Tasks Quick Reference

### Add New API Endpoint
```python
# In src/server/app.py
@app.get("/api/my-endpoint")
async def my_endpoint(db: Session = Depends(get_db_session)):
    provider = build_pm_provider(db_session=db)
    result = await provider.some_operation()
    return {"data": result}
```

### Create New MCP Tool
```python
# In mcp_server/tools/my_tool.py
MY_TOOL = Tool(
    name="my_tool",
    description="What it does",
    inputSchema={...}
)

async def my_tool_handler(arguments, context):
    # Implementation
    return [TextContent(type="text", text="Result")]
```

### Add New PM Provider
```python
# In pm_providers/my_provider.py
class MyProvider(BasePMProvider):
    async def list_projects(self) -> List[PMProject]:
        # Implementation
    
    async def create_task(self, task: PMTask) -> PMTask:
        # Implementation
```

## 📚 Documentation Quick Links

### Learning Materials
- 📖 [Learning Guide](file:///Users/phancao/.gemini/antigravity/brain/447e1910-5d4e-47e3-86f0-63087401e910/learning_guide.md) - Start here!
- 📄 [Codebase Overview](file:///Users/phancao/.gemini/antigravity/brain/447e1910-5d4e-47e3-86f0-63087401e910/codebase_overview.md) - Big picture
- 🏗️ [Architecture Deep Dive](file:///Users/phancao/.gemini/antigravity/brain/447e1910-5d4e-47e3-86f0-63087401e910/architecture_deep_dive.md) - Detailed diagrams
- ⚡ [Developer Quick Reference](file:///Users/phancao/.gemini/antigravity/brain/447e1910-5d4e-47e3-86f0-63087401e910/developer_quick_reference.md) - Commands & snippets

### Project Documentation
- 📘 [Main README](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/README.md)
- 🔧 [PM Providers README](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/pm_providers/README.md)
- 📁 [Project Structure](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/.project-structure.md)

## 🎓 Learning Path Summary

```
Week 1: Foundations
├── Read documentation
├── Set up environment
├── Understand architecture
└── Explore database

Week 2: Deep Dive
├── Study PM providers
├── Learn MCP server
├── Explore agents
└── Review frontend

Week 3: Contributing
├── Add new feature
├── Write tests
├── Update docs
└── Submit PR
```

## ✅ Quick Checklist

### Daily Development
- [ ] Pull latest changes
- [ ] Start Docker services
- [ ] Check service health
- [ ] Run tests before commit
- [ ] Format code
- [ ] Update documentation

### Before Committing
- [ ] Tests pass
- [ ] Code formatted
- [ ] No linting errors
- [ ] Documentation updated
- [ ] Changelog updated (if applicable)

### Before Deploying
- [ ] All tests pass
- [ ] Docker build succeeds
- [ ] Environment variables set
- [ ] Database migrations ready
- [ ] Rollback plan ready

---

**💡 Pro Tip**: Print this page and keep it on your desk for quick reference!

**Last Updated**: 2025-11-22
