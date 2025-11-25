# Project Management Agent - System Overview

> **Last Updated**: November 25, 2025  
> **Version**: 2.0  
> **Status**: Production-Ready

## 🎯 What Is This System?

The **Project Management Agent** is an AI-powered project management platform that combines:

- **Intelligent Research** via DeerFlow (deep research framework)
- **Multi-Agent Orchestration** via LangGraph
- **Unified PM Integration** supporting OpenProject, JIRA, ClickUp
- **Real-time Analytics** with 7+ chart types
- **Conversational Interface** with adaptive context gathering
- **MCP Protocol** for external tool integration

## 🏗️ System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[Next.js Web App]
        Chat[Chat Interface]
        Dashboard[PM Dashboard]
        Charts[Analytics Charts]
    end
    
    subgraph "API Gateway Layer"
        FastAPI[FastAPI Server]
        WS[WebSocket Handler]
        REST[REST Endpoints]
    end
    
    subgraph "Agent Orchestration"
        LG[LangGraph Workflow]
        CFM[Conversation Flow Manager]
        Agents[Multi-Agent System]
    end
    
    subgraph "Integration Layer"
        PMH[PM Handler]
        MCP[MCP Server]
        Analytics[Analytics Service]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL)]
        Redis[(Redis Cache)]
        Vector[(Vector DB)]
        External[External PM Systems]
    end
    
    UI --> FastAPI
    Chat --> WS
    Dashboard --> REST
    Charts --> REST
    
    FastAPI --> LG
    FastAPI --> CFM
    FastAPI --> PMH
    
    LG --> Agents
    CFM --> Agents
    
    Agents --> PMH
    Agents --> MCP
    Agents --> Analytics
    
    PMH --> PG
    PMH --> External
    MCP --> External
    Analytics --> PMH
    
    FastAPI --> Redis
    FastAPI --> PG
```

## 🔑 Core Components

### 1. **Frontend (Next.js + TypeScript)**
- **Location**: `web/`
- **Tech Stack**: Next.js 14, TypeScript, TailwindCSS, OpenAI ChatKit
- **Features**:
  - Real-time chat interface with streaming responses
  - Project/Task/Sprint dashboards
  - Analytics charts (burndown, velocity, CFD, etc.)
  - Responsive design for mobile/desktop

### 2. **Backend API (FastAPI + Python)**
- **Location**: `src/server/app.py`
- **Tech Stack**: FastAPI, Pydantic, Python 3.11+
- **Features**:
  - RESTful API endpoints
  - WebSocket for real-time updates
  - SSE (Server-Sent Events) for streaming
  - Health checks and monitoring

### 3. **Agent System (LangGraph + DeerFlow)**
- **Location**: `src/graph/`
- **Agents**:
  - **Coordinator**: Routes requests to appropriate agents
  - **Planner**: Creates research and execution plans
  - **Researcher**: Conducts web research using search tools
  - **Coder**: Executes Python code and calculations
  - **Reporter**: Generates final reports and responses
  - **Background Investigator**: Gathers context before planning

### 4. **Conversation Flow Manager**
- **Location**: `src/conversation/`
- **Purpose**: Adaptive conversation handling for PM tasks
- **Features**:
  - Intent classification (20+ intents)
  - Progressive context gathering
  - Validation and completeness checks
  - Self-learning from user feedback

### 5. **PM Providers (Unified Abstraction)**
- **Location**: `src/pm_providers/`
- **Supported Providers**:
  - ✅ OpenProject (v13 & v16)
  - 🚧 JIRA (in progress)
  - 📋 ClickUp (planned)
- **Operations**: Projects, Tasks, Sprints, Users, Time Entries

### 6. **Analytics Module**
- **Location**: `src/analytics/`
- **Charts Available**:
  - Burndown Chart
  - Velocity Chart
  - Sprint Report
  - Cumulative Flow Diagram (CFD)
  - Cycle Time Analysis
  - Work Distribution
  - Issue Trends

### 7. **MCP Server**
- **Location**: `src/mcp_servers/pm_server/`
- **Purpose**: Model Context Protocol server for external tool access
- **Transports**: stdio, HTTP, SSE
- **Features**: Authentication, RBAC, health checks

## 📊 Data Flow Patterns

### Pattern 1: User Chat → Research → Action
```
User Query
  ↓
Conversation Flow Manager (intent classification)
  ↓
LangGraph Workflow (plan creation)
  ↓
Agents (research/processing)
  ↓
PM Handler (execute actions)
  ↓
Response to User
```

### Pattern 2: Frontend Dashboard → REST API → PM Providers
```
Frontend Component
  ↓
REST API Call (/api/pm/*)
  ↓
PM Handler (multi-provider mode)
  ↓
Query ALL active providers
  ↓
Aggregate results
  ↓
Return to Frontend
```

### Pattern 3: Analytics Chart Generation
```
Frontend Chart Request
  ↓
Analytics API (/api/analytics/*)
  ↓
Analytics Service
  ↓
PM Adapter (fetch data)
  ↓
Calculator (process data)
  ↓
ChartResponse (JSON)
  ↓
Frontend renders chart
```

## 🗄️ Database Schema

### Core Tables
- **`users`** - User accounts and profiles
- **`projects`** - Internal project data
- **`tasks`** - Task information
- **`sprints`** - Sprint data
- **`pm_provider_connections`** - External PM system configurations
- **`project_sync_mappings`** - Internal ↔ External project mappings
- **`conversation_sessions`** - Chat session management

## 🚀 Deployment Architecture

### Docker Compose Services
1. **postgres** - Main PostgreSQL database (port 5432)
2. **redis** - Cache and session store (port 6379)
3. **api** - FastAPI backend (port 8000)
4. **frontend** - Next.js web app (port 3000)
5. **qdrant** - Vector database for RAG (port 6333)
6. **openproject** - OpenProject v16 instance (port 8082)
7. **openproject_v13** - OpenProject v13 instance (port 8083)
8. **mcp_postgres** - MCP server database (port 5435)
9. **pm_mcp_server** - MCP server (port 8080)

### Network Architecture
- All services run in `project_management_network`
- Internal communication via Docker service names
- External access via exposed ports

## 🔧 Configuration

### Environment Variables
```bash
# LLM
OPENAI_API_KEY=sk-...
BASIC_MODEL=gpt-4o-mini
REASONING_MODEL=o1-mini

# Database
DATABASE_URL=postgresql://pm_user:pm_password@postgres:5432/project_management

# PM Provider
PM_PROVIDER=openproject
OPENPROJECT_URL=http://localhost:8082
OPENPROJECT_API_KEY=...

# MCP Server
PM_MCP_SERVER_URL=http://pm_mcp_server:8080/sse
PM_MCP_API_KEY=mcp_...

# Search
SEARCH_API=duckduckgo
```

### Configuration Files
- **`.env`** - Environment variables
- **`conf.yaml`** - LLM and tool configurations
- **`docker-compose.yml`** - Service orchestration

## 📈 System Capabilities

### What Users Can Do
1. **Chat Naturally**: "Create a mobile app project with 3 sprints"
2. **Manage Projects**: Create, update, delete projects via UI or chat
3. **Plan Sprints**: AI-assisted sprint planning with capacity estimation
4. **Track Progress**: Real-time burndown charts and velocity metrics
5. **Research Topics**: Deep research integration for project planning
6. **Switch Providers**: Seamlessly work across OpenProject, JIRA, ClickUp
7. **Generate Reports**: Automated project reports and analytics

### What Developers Can Do
1. **Add New PM Providers**: Implement `BasePMProvider` interface
2. **Create Custom Charts**: Add calculators in `src/analytics/calculators/`
3. **Add Agent Tools**: Create tools in `src/tools/`
4. **Extend Conversation Flows**: Add intents in `ConversationFlowManager`
5. **Build Custom Agents**: Add nodes in `src/graph/nodes.py`

## 🎓 Learning Path

**For New Users**:
1. Read this overview
2. Review [02_architecture_deep_dive.md](./02_architecture_deep_dive.md)
3. Check [03_developer_guide.md](./03_developer_guide.md)
4. Explore [04_api_reference.md](./04_api_reference.md)

**For Developers**:
1. Start with [03_developer_guide.md](./03_developer_guide.md)
2. Review [05_component_reference.md](./05_component_reference.md)
3. Read [06_deployment_guide.md](./06_deployment_guide.md)
4. Check [07_testing_guide.md](./07_testing_guide.md)

## 📊 System Status

### ✅ Production-Ready
- DeerFlow research integration
- LangGraph multi-agent workflows
- OpenProject provider (v13 & v16)
- Analytics module (7 chart types)
- MCP Server (stdio/HTTP/SSE)
- REST API and WebSocket
- Frontend dashboard

### 🚧 In Progress
- JIRA provider implementation
- ClickUp provider implementation
- Real-time sync with external systems

### 📋 Planned
- Asana provider
- Trello provider
- Webhooks for external updates
- ML-based predictions
- Multi-tenant support

---

**Next**: [Architecture Deep Dive →](./02_architecture_deep_dive.md)
