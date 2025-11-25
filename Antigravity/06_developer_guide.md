# Developer Quick Start Guide

> **Last Updated**: November 25, 2025

## 🎯 Getting Started

### Prerequisites

- **Python 3.11+** with `uv` package manager
- **Node.js 18+** with `pnpm`
- **Docker** and **Docker Compose**
- **Git**
- **OpenAI API Key**

### Local Development Setup

#### 1. Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd Project-Management-Agent

# Install Python dependencies
uv sync

# Install frontend dependencies
cd web && pnpm install && cd ..

# Copy environment file
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

#### 2. Start Infrastructure

```bash
# Start databases only
docker-compose up -d postgres redis qdrant

# Or start everything including OpenProject
docker-compose up -d
```

#### 3. Run Backend Locally

```bash
# Run database migrations
uv run alembic upgrade head

# Start FastAPI server
uv run uvicorn src.server.app:app --reload --port 8000

# Or use the shortcut
make dev-api
```

#### 4. Run Frontend Locally

```bash
cd web
pnpm run dev
```

#### 5. Run MCP Server Locally

```bash
# Start MCP server with SSE transport
python scripts/run_pm_mcp_server.py --transport sse --port 8080

# Or with stdio transport
python scripts/run_pm_mcp_server.py --transport stdio
```

## 🏗️ Project Structure

```
Project-Management-Agent/
├── src/                      # Backend Python code
│   ├── graph/                # LangGraph workflows
│   ├── conversation/         # Conversation flow manager
│   ├── pm_providers/         # PM integrations
│   ├── analytics/            # Analytics module
│   ├── mcp_servers/          # MCP server
│   ├── server/               # FastAPI app
│   ├── tools/                # Agent tools
│   ├── handlers/             # Business logic
│   └── prompts/              # LLM prompts
├── web/                      # Frontend Next.js app
│   └── src/
│       ├── app/              # Pages
│       ├── components/       # React components
│       ├── core/             # API & state
│       └── hooks/            # Custom hooks
├── tests/                    # Pytest tests
├── scripts/                  # Utility scripts
├── database/                 # SQL schemas
├── docker-compose.yml        # Docker services
├── pyproject.toml            # Python dependencies
└── Makefile                  # Common commands
```

## 🔨 Common Development Tasks

### Adding a New PM Provider

#### 1. Create Provider Class

```python
# src/pm_providers/asana.py
from typing import List, Optional
from .base import BasePMProvider
from .models import PMProject, PMTask

class AsanaProvider(BasePMProvider):
    def __init__(self, config: dict):
        self.api_token = config["api_token"]
        self.workspace_id = config["workspace_id"]
        self.base_url = "https://app.asana.com/api/1.0"
    
    async def list_projects(self) -> List[PMProject]:
        # Implementation
        pass
    
    async def list_tasks(
        self, 
        project_id: Optional[str] = None
    ) -> List[PMTask]:
        # Implementation
        pass
    
    # Implement all abstract methods from BasePMProvider
```

#### 2. Register in Factory

```python
# src/pm_providers/factory.py
from .asana import AsanaProvider

PROVIDER_REGISTRY = {
    "internal": InternalProvider,
    "openproject": OpenProjectProvider,
    "jira": JiraProvider,
    "asana": AsanaProvider,  # Add here
}
```

#### 3. Add Configuration

```python
# .env
PM_PROVIDER=asana
ASANA_API_TOKEN=your-token
ASANA_WORKSPACE_ID=your-workspace-id
```

### Adding a New Analytics Chart

#### 1. Create Calculator

```python
# src/analytics/calculators/epic_progress.py
from typing import Dict, Any
from ..models import ChartResponse

class EpicProgressCalculator:
    @staticmethod
    def calculate(epic_data: Dict[str, Any]) -> ChartResponse:
        # Process data
        completed_tasks = len([t for t in epic_data["tasks"] if t["status"] == "done"])
        total_tasks = len(epic_data["tasks"])
        
        return ChartResponse(
            chart_type="epic_progress",
            title=f"Epic: {epic_data['name']}",
            data={
                "completed": completed_tasks,
                "total": total_tasks,
                "progress": completed_tasks / total_tasks if total_tasks > 0 else 0
            },
            metadata={
                "epic_id": epic_data["id"],
                "epic_name": epic_data["name"]
            }
        )
```

#### 2. Add to Analytics Service

```python
# src/analytics/service.py
from .calculators.epic_progress import EpicProgressCalculator

class AnalyticsService:
    def get_epic_progress(self, epic_id: str) -> ChartResponse:
        epic_data = self.adapter.get_epic_data(epic_id)
        return EpicProgressCalculator.calculate(epic_data)
```

#### 3. Add API Endpoint

```python
# src/server/app.py
@app.get("/api/analytics/epics/{epic_id}/progress")
async def get_epic_progress(epic_id: str):
    service = AnalyticsService(data_source="pm_providers")
    return service.get_epic_progress(epic_id)
```

### Adding a New Agent Tool

#### 1. Create Tool Function

```python
# src/tools/custom_tools.py
from langchain.tools import tool

@tool
def analyze_project_risk(project_id: str) -> str:
    """
    Analyze project risks based on current status and metrics.
    
    Args:
        project_id: The project ID to analyze
    
    Returns:
        Risk analysis report as string
    """
    # Implementation
    pm_handler = get_pm_handler()
    project = pm_handler.get_project(project_id)
    tasks = pm_handler.list_tasks(project_id)
    
    # Analyze risks
    overdue_tasks = [t for t in tasks if is_overdue(t)]
    high_priority_incomplete = [
        t for t in tasks 
        if t.priority == "high" and t.status != "done"
    ]
    
    risk_score = calculate_risk_score(overdue_tasks, high_priority_incomplete)
    
    return f"Risk Analysis for {project.name}:\n" \
           f"Risk Score: {risk_score}/10\n" \
           f"Overdue Tasks: {len(overdue_tasks)}\n" \
           f"High Priority Incomplete: {len(high_priority_incomplete)}"
```

#### 2. Register Tool

```python
# src/graph/nodes.py
from src.tools.custom_tools import analyze_project_risk

def researcher_node(state: State) -> State:
    tools = [
        get_web_search_tool(),
        crawl_tool,
        *get_pm_tools(),
        *get_analytics_tools(),
        analyze_project_risk,  # Add here
    ]
    
    # Rest of implementation
```

### Adding a New Conversation Intent

#### 1. Define Intent

```python
# src/conversation/flow_manager.py
class Intent(Enum):
    # Existing intents...
    ANALYZE_RISKS = "analyze_risks"  # Add new intent
```

#### 2. Add Required Fields

```python
REQUIRED_FIELDS = {
    # Existing mappings...
    Intent.ANALYZE_RISKS: ["project_id"],
}
```

#### 3. Add Intent Handler

```python
async def _execute_intent(
    self, 
    intent: Intent, 
    entities: Dict[str, Any]
) -> ConversationResponse:
    if intent == Intent.ANALYZE_RISKS:
        return await self._handle_analyze_risks(entities)
    # ... other handlers
    
async def _handle_analyze_risks(
    self, 
    entities: Dict[str, Any]
) -> ConversationResponse:
    project_id = entities["project_id"]
    
    # Use the tool we created
    from src.tools.custom_tools import analyze_project_risk
    result = analyze_project_risk(project_id)
    
    return ConversationResponse(
        message=result,
        intent=Intent.ANALYZE_RISKS,
        completed=True
    )
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_pm_providers.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_pm_providers.py::test_list_projects

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x
```

### Writing Tests

```python
# tests/test_custom_feature.py
import pytest
from src.pm_providers.asana import AsanaProvider

@pytest.fixture
def asana_provider():
    config = {
        "api_token": "test-token",
        "workspace_id": "test-workspace"
    }
    return AsanaProvider(config)

async def test_list_projects(asana_provider):
    projects = await asana_provider.list_projects()
    assert isinstance(projects, list)
    assert len(projects) > 0

async def test_create_task(asana_provider):
    task = await asana_provider.create_task(
        project_id="proj-123",
        title="Test Task",
        description="Test description"
    )
    assert task.title == "Test Task"
```

## 🐛 Debugging

### Enable Debug Logging

```bash
# Set environment variable
export DEBUG_PM=true

# Or in .env
DEBUG_PM=true

# Run with debug logging
uv run uvicorn src.server.app:app --reload --log-level debug
```

### Debug in VS Code

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
        "src.server.app:app",
        "--reload",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false
    },
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    }
  ]
}
```

### Debug LangGraph Workflow

```python
# Enable LangGraph debug mode
import logging
logging.getLogger("langgraph").setLevel(logging.DEBUG)

# Run workflow with debug flag
from src.workflow import run_agent_workflow_async

await run_agent_workflow_async(
    "your query",
    debug=True  # Enables detailed logging
)
```

## 📝 Code Style

### Python (PEP 8)

```bash
# Format code
uv run black src/

# Check linting
uv run flake8 src/

# Type checking
uv run mypy src/

# Sort imports
uv run isort src/
```

### TypeScript/React

```bash
cd web

# Format code
pnpm run format

# Lint
pnpm run lint

# Type check
pnpm run type-check
```

## 🔄 Git Workflow

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Code refactoring
- `test/` - Test additions

### Commit Messages

```bash
# Format: <type>(<scope>): <subject>

git commit -m "feat(pm-providers): add Asana provider"
git commit -m "fix(analytics): correct burndown calculation"
git commit -m "docs(api): update endpoint documentation"
```

## 🚀 Deployment

### Build Docker Images

```bash
# Build all images
docker-compose build

# Build specific service
docker-compose build api

# Build with no cache
docker-compose build --no-cache
```

### Environment-Specific Configs

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d

# Testing
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 📚 Useful Commands

### Makefile Commands

```bash
# Development
make dev-api          # Run API locally
make dev-frontend     # Run frontend locally
make dev-mcp          # Run MCP server locally

# Testing
make test             # Run all tests
make test-coverage    # Run tests with coverage

# Docker
make docker-up        # Start all services
make docker-down      # Stop all services
make docker-logs      # View logs

# Database
make db-migrate       # Run migrations
make db-reset         # Reset database
```

### Database Migrations

```bash
# Create new migration
uv run alembic revision -m "add new table"

# Run migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Show current version
uv run alembic current
```

---

**Next**: [Troubleshooting Guide →](./07_troubleshooting.md)
