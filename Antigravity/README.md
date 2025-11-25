# Antigravity Documentation - Project Management Agent

> **Documentation Suite for AI-Powered Project Management System**  
> **Last Updated**: November 25, 2025

## 📚 Documentation Index

This folder contains comprehensive documentation for the Project Management Agent system, designed to help developers, users, and AI assistants understand and work with the codebase.

### 📖 Documentation Files

1. **[01_system_overview.md](./01_system_overview.md)**
   - High-level system architecture
   - Core components overview
   - Technology stack
   - Deployment architecture
   - Learning paths for different roles

2. **[02_backend_components.md](./02_backend_components.md)**
   - Detailed backend module reference
   - LangGraph workflow architecture
   - Conversation flow manager
   - PM providers abstraction
   - Analytics module
   - MCP server implementation

3. **[03_frontend_architecture.md](./03_frontend_architecture.md)**
   - Next.js app structure
   - API integration patterns
   - State management with Zustand
   - Custom React hooks
   - Component architecture
   - Data flow patterns

4. **[04_api_reference.md](./04_api_reference.md)**
   - Complete REST API documentation
   - Chat and conversation endpoints
   - PM management endpoints
   - Analytics endpoints
   - WebSocket events
   - Error handling

5. **[05_deployment_guide.md](./05_deployment_guide.md)**
   - Docker Compose setup
   - Service architecture
   - Configuration files
   - Health checks
   - Common operations
   - Troubleshooting
   - Security considerations

6. **[06_developer_guide.md](./06_developer_guide.md)**
   - Local development setup
   - Adding new features
   - Testing guidelines
   - Debugging techniques
   - Code style standards
   - Git workflow

7. **[07_workflows_and_dataflows.md](./07_workflows_and_dataflows.md)**
   - Core workflow diagrams
   - Data flow patterns
   - State management flows
   - Authentication flows
   - Real-time update patterns

## 🎯 Quick Navigation

### For New Users
Start here to understand what the system does:
1. [System Overview](./01_system_overview.md) - What is this system?
2. [Deployment Guide](./05_deployment_guide.md) - How to run it?
3. [API Reference](./04_api_reference.md) - How to use it?

### For Developers
Start here to contribute to the codebase:
1. [Developer Guide](./06_developer_guide.md) - Setup and development
2. [Backend Components](./02_backend_components.md) - Backend architecture
3. [Frontend Architecture](./03_frontend_architecture.md) - Frontend architecture
4. [Workflows](./07_workflows_and_dataflows.md) - How everything connects

### For AI Assistants
Start here to understand the codebase:
1. [System Overview](./01_system_overview.md) - High-level architecture
2. [Backend Components](./02_backend_components.md) - Backend details
3. [Frontend Architecture](./03_frontend_architecture.md) - Frontend details
4. [Workflows](./07_workflows_and_dataflows.md) - Data flows and patterns

## 🏗️ System Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│              Frontend (Next.js + TypeScript)            │
│  - Chat Interface  - Dashboards  - Analytics Charts    │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│            API Gateway (FastAPI + Python)               │
│  - REST APIs  - WebSocket  - SSE Streaming             │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│          Agent Orchestration (LangGraph)                │
│  - Multi-Agent Workflows  - Conversation Flow Manager  │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│     Integration Layer (PM Handler + MCP Server)         │
│  - PM Providers  - Analytics  - External Tools         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│   Data Layer (PostgreSQL + Redis + Vector DB)          │
│  - Projects  - Tasks  - Sprints  - Analytics           │
└─────────────────────────────────────────────────────────┘
```

## 🔑 Key Features

- **AI-Powered Conversations**: Natural language interface for PM operations
- **Multi-Provider Support**: OpenProject, JIRA, ClickUp integration
- **Real-time Analytics**: 7+ chart types with server-side generation
- **Agent Orchestration**: LangGraph-based multi-agent workflows
- **MCP Protocol**: External tool integration via Model Context Protocol
- **Responsive UI**: Modern Next.js frontend with real-time updates

## 📊 Technology Stack

### Backend
- Python 3.11+, FastAPI, LangGraph, DeerFlow
- PostgreSQL, Redis, Qdrant (vector DB)
- OpenAI GPT-4o-mini, LangChain

### Frontend
- Next.js 14, TypeScript, TailwindCSS
- Zustand (state), React Query (data)
- OpenAI ChatKit, Recharts

### Infrastructure
- Docker & Docker Compose
- OpenProject (v13 & v16)
- MCP Server (stdio/HTTP/SSE)

## 🚀 Quick Start

```bash
# Clone repository
git clone <repository-url>
cd Project-Management-Agent

# Configure environment
cp .env.example .env
# Edit .env and add OPENAI_API_KEY

# Start all services
docker-compose up -d

# Access applications
# Frontend: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## 📝 Documentation Standards

All documentation in this folder follows these standards:

- **Mermaid Diagrams**: For architecture and flow diagrams
- **Code Examples**: Real, working code snippets
- **Clear Structure**: Consistent headings and organization
- **Cross-References**: Links between related documents
- **Up-to-Date**: Last updated dates on all documents

## 🤝 Contributing to Documentation

When updating documentation:

1. **Update the date** at the top of the file
2. **Keep examples current** with the actual codebase
3. **Add cross-references** to related documents
4. **Use consistent formatting** (Markdown + Mermaid)
5. **Test code examples** before committing

## 📞 Support

For questions or issues:
- Check the [Troubleshooting section](./05_deployment_guide.md#-troubleshooting) in the Deployment Guide
- Review the [Developer Guide](./06_developer_guide.md) for development issues
- Consult the [API Reference](./04_api_reference.md) for API questions

---

**Built with ❤️ by the Project Management Agent Team**
