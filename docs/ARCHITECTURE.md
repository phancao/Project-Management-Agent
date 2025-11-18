# Project Management Agent - Hybrid Architecture

## 🎯 Tổng quan hệ thống

Hệ thống quản lý dự án thông minh kết hợp:
- **DeerFlow**: Deep research và knowledge gathering
- **OpenAI AgentSDK**: Action-oriented project management
- **OpenAI ChatKit**: Modern chat interface
- **Conversation Flow Management**: Adaptive conversation system

## 🏗️ Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  Next.js + TypeScript + OpenAI ChatKit                        │
│  - Real-time chat interface                                   │
│  - Project dashboard                                          │
│  - Task management UI                                         │
│  - Team collaboration tools                                   │
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
│  - Rate limiting & validation                                 │
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
│  - Multi-turn conversation handling                           │
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
│  - Research results storage                                   │
└─────────────────────────────────────────────────────────────────┘
```

## 🤖 Agent Architecture

### 1. DeerFlow Research Agents
```
Coordinator → Planner → Researcher → Coder → Reporter
     ↓
Background Investigation
     ↓
Knowledge Base Update
```

### 2. AgentSDK Project Management Agents
```
Project Manager Agent
├── Task Planner Agent
├── Resource Manager Agent
├── Timeline Agent
└── Quality Assurance Agent
```

### 3. Custom Conversation Agents
```
Conversation Flow Manager
├── Intent Classifier (LLM-powered)
├── Context Manager
├── Data Gatherer (LLM-powered extraction)
├── Action Executor
└── Self-Learning System
    ├── Pattern Learner
    ├── Metrics Tracker
    └── Feedback Processor
```

## 💬 Conversation Flow Management

### Flow States
1. **Intent Detection**: LLM-powered intent classification with 14 intent types
2. **Context Gathering**: Progressive data collection with LLM extraction
3. **Research Phase**: Sử dụng DeerFlow để research
4. **Planning Phase**: Sử dụng AgentSDK để lập kế hoạch
5. **Execution Phase**: Thực hiện các action
6. **Feedback Phase**: Thu thập feedback và self-learning

### LLM-Based Intent Understanding
```python
class IntentClassifier:
    """Classifies user intent using LLM with fallback to keywords"""
    
    async def classify(self, message: str, conversation_history: List[Dict]) -> IntentType:
        # Uses LLM to understand natural language
        # Returns one of 14 intent types:
        # - CREATE_PROJECT, PLAN_TASKS, RESEARCH_TOPIC
        # - CREATE_WBS, SPRINT_PLANNING, ASSIGN_TASKS
        # - CHECK_RESOURCES, CREATE_REPORT, etc.
        return await self._classify_with_llm(message, conversation_history)
```

### Self-Learning System
```python
class SelfLearningSystem:
    """Continuously improves intent classification"""
    
    def record_classification(self, message, classified_intent, confidence):
        # Stores every classification for analysis
        
    def record_feedback(self, classification_id, was_correct, corrected_intent):
        # Updates patterns and metrics when user corrects
        
    def _learn_pattern(self, message, correct_intent, wrong_intent):
        # Learns: "setup sprint" → CREATE_PROJECT (after correction)
        # Calculates confidence: success_count / (success + failure)
```

### Adaptive Question Generation & Data Extraction
```python
class DataExtractor:
    """Extracts structured data from natural language using LLM"""
    
    async def extract_project_data(self, message: str, intent: IntentType) -> Dict:
        # Message: "I need a mobile app with $50k budget"
        # Extracts: {"description": "mobile app", "budget": 50000}
        # Reduces need for multiple clarification questions
```

## 🗄️ Database Schema

### Core Tables
```sql
-- Projects
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Tasks
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50),
    priority INTEGER,
    estimated_hours DECIMAL(5,2),
    actual_hours DECIMAL(5,2),
    due_date TIMESTAMP,
    created_at TIMESTAMP
);

-- Team Members
CREATE TABLE team_members (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    role VARCHAR(100),
    skills TEXT[],
    created_at TIMESTAMP
);

-- Research Sessions
CREATE TABLE research_sessions (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    topic TEXT NOT NULL,
    research_data JSONB,
    created_at TIMESTAMP
);

-- Knowledge Base
CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    metadata JSONB,
    created_at TIMESTAMP
);

-- Self-Learning Tables
CREATE TABLE intent_classifications (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES conversation_sessions(id),
    message TEXT NOT NULL,
    classified_intent VARCHAR(50) NOT NULL,
    confidence_score FLOAT,
    was_correct BOOLEAN,
    user_corrected_intent VARCHAR(50),
    conversation_history JSONB,
    created_at TIMESTAMP
);

CREATE TABLE intent_feedback (
    id UUID PRIMARY KEY,
    classification_id UUID REFERENCES intent_classifications(id),
    feedback_type VARCHAR(20),
    original_message TEXT,
    suggested_intent VARCHAR(50),
    user_comment TEXT,
    created_at TIMESTAMP
);

CREATE TABLE intent_metrics (
    intent_type VARCHAR(50) PRIMARY KEY,
    total_classifications INTEGER,
    correct_classifications INTEGER,
    success_rate FLOAT,
    average_confidence FLOAT,
    last_updated TIMESTAMP
);

CREATE TABLE learned_intent_patterns (
    id UUID PRIMARY KEY,
    intent_type VARCHAR(50),
    pattern_text TEXT NOT NULL,
    success_count INTEGER,
    failure_count INTEGER,
    pattern_type VARCHAR(20),
    confidence FLOAT,
    created_at TIMESTAMP,
    last_used_at TIMESTAMP
);
```

## 🔄 API Endpoints

### Core APIs
```python
# Project Management
POST   /api/projects                    # Create project
GET    /api/projects                    # List projects
GET    /api/projects/{id}               # Get project details
PUT    /api/projects/{id}               # Update project
DELETE /api/projects/{id}               # Delete project

# Task Management
POST   /api/projects/{id}/tasks         # Create task
GET    /api/projects/{id}/tasks         # List tasks
PUT    /api/tasks/{id}                  # Update task
DELETE /api/tasks/{id}                  # Delete task

# Research & Knowledge
POST   /api/research                    # Start research session
GET    /api/research/{id}               # Get research results
POST   /api/knowledge/search            # Search knowledge base

# Conversation & Self-Learning
POST   /api/chat                        # Send message (auto-records classification)
GET    /api/chat/history                # Get chat history
POST   /api/intent/feedback             # Provide feedback on classification
GET    /api/intent/metrics              # Get classification performance metrics
WebSocket /ws/chat                      # Real-time chat
```

## 🚀 Implementation Plan

### Phase 1: Core Infrastructure
1. ✅ DeerFlow integration
2. ✅ Conversation Flow Manager (LLM-based)
3. ✅ Database schema setup (with self-learning tables)
4. ✅ Basic API endpoints (with feedback APIs)
5. ✅ Self-learning system (fully implemented)

### Phase 2: AgentSDK Integration
1. 🔄 Project Management Agents
2. 🔄 Action execution system
3. 🔄 Knowledge base integration

### Phase 3: Frontend & UI
1. 🔄 Next.js setup
2. 🔄 ChatKit integration
3. 🔄 Project dashboard
4. 🔄 Real-time updates

### Phase 4: Advanced Features
1. ✅ Self-learning system (Implemented and tested)
2. 🔄 Advanced analytics
3. 🔄 Team collaboration
4. 🔄 Mobile app

## 🧠 Intent Types & Self-Learning

### Supported Intent Types (14 total)
1. **CREATE_PROJECT** - Create a new project
2. **PLAN_TASKS** - Plan or break down tasks
3. **RESEARCH_TOPIC** - Research a topic using DeerFlow
4. **UPDATE_PROJECT** - Update an existing project
5. **GET_STATUS** - Check project status or progress
6. **CREATE_WBS** - Create Work Breakdown Structure
7. **SPRINT_PLANNING** - Plan a sprint or sprint cycle
8. **ASSIGN_TASKS** - Assign tasks to team members
9. **CHECK_RESOURCES** - Check resource availability
10. **CREATE_REPORT** - Generate a report
11. **TASK_BREAKDOWN** - Break down tasks into subtasks
12. **DEPENDENCY_ANALYSIS** - Analyze task dependencies
13. **GANTT_CHART** - Create or view Gantt chart/timeline
14. **HELP** - Get help or know what the system can do

### Self-Learning Workflow
```
User Message
    ↓
LLM Classifies Intent
    ↓
System Records Classification
    ↓
User Provides Feedback (if wrong)
    ↓
System Learns Pattern
    ↓
High-Confidence Patterns Enhance Future Classifications
```

### Example Learning Cycle
**Day 1:**
- User: "setup sprint"
- System: Classifies as SPRINT_PLANNING
- User: "No, I meant create project"
- System: Learns pattern → "setup sprint" → CREATE_PROJECT

**Day 7:**
- User: "setup sprint"
- System: Correctly classifies as CREATE_PROJECT ✅
- Pattern confidence: 100% (10/10 successes)

## 🔧 Technology Stack

### Backend
- **Python 3.11+**
- **FastAPI** - API framework
- **DeerFlow** - Research framework
- **OpenAI AgentSDK** - Agent framework
- **PostgreSQL** - Primary database
- **SQLAlchemy** - ORM (Object-Relational Mapping)
- **pgvector** - Vector extension for PostgreSQL
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

## 📊 Key Features

### 1. LLM-Powered Intent Understanding ⭐ NEW
- Natural language intent classification using GPT
- 14 intent types including WBS, sprint planning, reports
- Context-aware understanding with conversation history
- Automatic data extraction from messages

### 2. Self-Learning Conversation System ⭐ NEW
- Records every intent classification
- Learns from user corrections automatically
- Builds pattern library over time
- Improves classification accuracy from 60% → 85%+

### 3. Intelligent Project Planning
- Research-based project estimation using DeerFlow
- Automatic task breakdown
- Resource allocation
- Risk assessment

### 4. Adaptive Conversation System
- Context-aware conversations
- Progressive data gathering with LLM extraction
- Self-learning flows
- Multi-language support

### 5. Knowledge Management
- Research result storage
- Semantic search
- Knowledge base updates
- Team knowledge sharing

## 🆕 Recent Improvements (Latest Version)

### LLM-Based Intent Classification
- **Replaced**: Simple keyword matching
- **With**: LLM-powered intent understanding
- **Benefits**: Natural language understanding, 14 intent types, context awareness

### Self-Learning System
- **New Feature**: Continuous improvement from user feedback
- **Tables**: intent_classifications, intent_feedback, intent_metrics, learned_intent_patterns
- **API Endpoints**: POST /api/intent/feedback, GET /api/intent/metrics

### Data Extraction
- **New Feature**: LLM-powered structured data extraction
- **Benefits**: Understands "mobile app with $50k budget" automatically
- **Reduces**: Need for multiple clarification questions

### 6. Real-time Collaboration
- Live chat interface
- Real-time updates
- Team notifications
- Progress tracking

## 🎯 Success Metrics

1. **User Experience**: Smooth conversation flows
2. **Accuracy**: High-quality project plans
3. **Efficiency**: Reduced planning time
4. **Learning**: System improvement over time
5. **Adoption**: Team engagement and usage
