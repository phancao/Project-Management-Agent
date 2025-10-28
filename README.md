# Project Management Agent

A sophisticated AI-powered project management system that combines deep research capabilities with intelligent conversation flow management. Built with DeerFlow, OpenAI AgentSDK, and modern web technologies.

## 🚀 Features

### Core Capabilities
- **Intelligent Project Planning**: AI-driven project creation with research-backed estimates
- **Adaptive Conversation System**: Context-aware conversations that guide users to provide complete information
- **Deep Research Integration**: Leverages DeerFlow for comprehensive topic research and knowledge gathering
- **Real-time Collaboration**: Live chat interface with WebSocket support
- **Knowledge Management**: Vector-based knowledge base with semantic search
- **Self-Learning System**: Adapts conversation flows based on user interactions

### Technical Features
- **Multi-Agent Architecture**: Coordinated agents for different aspects of project management
- **Conversation Flow Management**: Progressive data gathering with intelligent question generation
- **Vector Search**: Semantic search across research results and knowledge base
- **Real-time Updates**: WebSocket-based live updates and notifications
- **Responsive UI**: Modern, mobile-friendly interface built with Next.js and Tailwind CSS

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  Next.js + TypeScript + OpenAI ChatKit                        │
│  - Real-time chat interface                                   │
│  - Project dashboard                                          │
│  - Task management UI                                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway Layer                       │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI + Pydantic                                           │
│  - RESTful APIs                                               │
│  - WebSocket for real-time updates                            │
│  - Authentication & Authorization                             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Conversation Flow Manager                   │
├─────────────────────────────────────────────────────────────────┤
│  - Intent classification                                      │
│  - Context management                                         │
│  - Progressive data gathering                                 │
│  - Self-learning conversation flows                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Agent Orchestration                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   DeerFlow      │  │   AgentSDK      │  │   Custom        │  │
│  │   Research      │  │   Project Mgmt  │  │   Agents        │  │
│  │   Agents        │  │   Agents        │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data & Knowledge Layer                    │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL + Vector Store + Redis                            │
│  - Project data (relational)                                  │
│  - Knowledge base (vector)                                    │
│  - Session cache (Redis)                                      │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠️ Technology Stack

### Backend
- **Python 3.11+** - Core language
- **FastAPI** - API framework
- **DeerFlow** - Deep research framework
- **OpenAI AgentSDK** - Agent framework
- **PostgreSQL** - Primary database
- **Qdrant** - Vector database
- **Redis** - Caching & sessions
- **Docker** - Containerization

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **OpenAI ChatKit** - Chat interface
- **Tailwind CSS** - Styling
- **Socket.io** - Real-time communication

### AI & ML
- **OpenAI GPT-4o-mini** - LLM
- **OpenAI Embeddings** - Vector embeddings
- **LangChain** - LLM framework
- **LangGraph** - Agent workflows

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI API key
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd project-management-agent
```

### 2. Environment Setup
Create a `.env` file in the root directory:
```bash
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=postgresql://pm_user:pm_password@localhost:5432/project_management
REDIS_URL=redis://localhost:6379
```

### 3. Run with Docker Compose
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🧪 Development Setup

### Backend Development
```bash
# Install dependencies
uv sync

# Run database migrations
uv run alembic upgrade head

# Start the API server
uv run uvicorn api.main:app --reload --port 8000
```

### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Database Setup
```bash
# Start PostgreSQL
docker-compose up postgres -d

# Run schema setup
psql -h localhost -U pm_user -d project_management -f database/schema.sql
```

## 📚 API Documentation

### Core Endpoints

#### Chat & Conversation
- `POST /api/chat` - Send message to conversation flow manager
- `GET /api/chat/history/{session_id}` - Get chat history
- `WebSocket /ws/chat/{session_id}` - Real-time chat

#### Project Management
- `POST /api/projects` - Create new project
- `GET /api/projects` - List projects
- `GET /api/projects/{id}` - Get project details
- `PUT /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project

#### Task Management
- `POST /api/projects/{id}/tasks` - Create task
- `GET /api/projects/{id}/tasks` - List tasks
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task

#### Research & Knowledge
- `POST /api/research` - Start research session
- `GET /api/research/{id}` - Get research results
- `POST /api/knowledge/search` - Search knowledge base

## 🤖 Agent System

### Conversation Flow Manager
The system uses an intelligent conversation flow manager that:

1. **Intent Detection**: Classifies user requests (create project, plan tasks, research, etc.)
2. **Context Gathering**: Progressively collects required information
3. **Research Phase**: Uses DeerFlow for deep research when needed
4. **Planning Phase**: Uses AgentSDK for project planning and task breakdown
5. **Execution Phase**: Performs the requested actions
6. **Learning**: Adapts conversation flows based on interactions

### Agent Types
- **Coordinator Agent**: Routes requests and manages workflow
- **Research Agent**: Conducts deep research using DeerFlow
- **Project Manager Agent**: Handles project creation and management
- **Task Planner Agent**: Breaks down projects into actionable tasks
- **Knowledge Agent**: Manages knowledge base and search

## 🗄️ Database Schema

### Core Tables
- `users` - User accounts and profiles
- `projects` - Project information and metadata
- `tasks` - Individual tasks within projects
- `team_members` - Project team assignments
- `research_sessions` - Research session data
- `knowledge_base` - Vector-stored knowledge items
- `conversation_sessions` - Chat session management
- `project_metrics` - Analytics and metrics

## 🔧 Configuration

### Environment Variables
```bash
# Required
OPENAI_API_KEY=your_openai_api_key

# Database
DATABASE_URL=postgresql://user:pass@host:port/db
REDIS_URL=redis://host:port

# Optional
ENVIRONMENT=development
LOG_LEVEL=INFO
MAX_CONVERSATION_HISTORY=100
```

### DeerFlow Configuration
The system uses DeerFlow's configuration in `conf.yaml`:
```yaml
BASIC_MODEL:
  base_url: "https://api.openai.com/v1"
  model: "gpt-4o-mini"
  api_key: "your_openai_api_key"

SEARCH_ENGINE:
  engine: duckduckgo
```

## 🧪 Testing

### Run Tests
```bash
# Backend tests
uv run pytest

# Frontend tests
cd frontend && npm test

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Test Coverage
```bash
# Backend coverage
uv run pytest --cov=src --cov-report=html

# Frontend coverage
cd frontend && npm run test:coverage
```

## 📊 Monitoring & Analytics

### Health Checks
- API Health: `GET /health`
- Database Health: Built-in PostgreSQL health checks
- Redis Health: Built-in Redis health checks

### Metrics
- Conversation success rates
- Project completion rates
- Research accuracy metrics
- User engagement analytics

## 🚀 Deployment

### Production Deployment
```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy to production
docker-compose -f docker-compose.prod.yml up -d
```

### Environment-Specific Configs
- `docker-compose.yml` - Development
- `docker-compose.prod.yml` - Production
- `docker-compose.test.yml` - Testing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use TypeScript for frontend code
- Write tests for new features
- Update documentation as needed

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [DeerFlow](https://github.com/bytedance/deer-flow) - Deep research framework
- [OpenAI](https://openai.com/) - AI models and tools
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Next.js](https://nextjs.org/) - React framework
- [Tailwind CSS](https://tailwindcss.com/) - CSS framework

## 📞 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation wiki

---

**Built with ❤️ by the Project Management Agent Team**