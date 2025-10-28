"""
FastAPI server for Project Management Agent

This module provides RESTful APIs and WebSocket endpoints for the project management system.
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import uuid
from datetime import datetime

from src.conversation.flow_manager import ConversationFlowManager, ConversationContext
from src.agents.deerflow_integration import deerflow_pm_integration
from src.agents.pm_agent_manager import AgentType
from database.models import (
    Project, ProjectCreate, ProjectUpdate, 
    Task, TaskCreate, TaskUpdate,
    User, UserCreate
)

# Initialize FastAPI app
app = FastAPI(
    title="Project Management Agent API",
    description="AI-powered project management system with conversation flow management",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize conversation flow manager
flow_manager = ConversationFlowManager()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(json.dumps(message))

manager = ConnectionManager()

# Pydantic models for API
class ChatMessage(BaseModel):
    message: str
    session_id: str
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    type: str
    message: str
    state: Optional[str] = None
    intent: Optional[str] = None
    missing_fields: Optional[List[str]] = None
    data: Optional[Dict[str, Any]] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # TODO: Implement proper JWT authentication
    # For now, return a mock user
    return {"user_id": "mock_user_id", "email": "user@example.com"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Chat endpoints
@app.post("/api/chat", response_model=ChatResponse)
async def send_message(
    message: ChatMessage,
    current_user: dict = Depends(get_current_user)
):
    """Send a message to the conversation flow manager"""
    try:
        response = await flow_manager.process_message(
            message=message.message,
            session_id=message.session_id,
            user_id=current_user.get("user_id")
        )
        return ChatResponse(**response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history/{session_id}")
async def get_chat_history(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get chat history for a session"""
    if session_id in flow_manager.contexts:
        context = flow_manager.contexts[session_id]
        return {
            "session_id": session_id,
            "history": context.conversation_history,
            "current_state": context.current_state.value,
            "intent": context.intent.value
        }
    return {"session_id": session_id, "history": [], "current_state": "new", "intent": "unknown"}

# WebSocket endpoint for real-time chat
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process message through flow manager
            response = await flow_manager.process_message(
                message=message_data["message"],
                session_id=session_id,
                user_id=message_data.get("user_id")
            )
            
            # Send response back
            await manager.send_message(session_id, response)
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)

# Project management endpoints
@app.post("/api/projects", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new project"""
    # TODO: Implement project creation with database
    project_id = str(uuid.uuid4())
    return ProjectResponse(
        id=project_id,
        name=project.name,
        description=project.description,
        status="planning",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@app.get("/api/projects", response_model=List[ProjectResponse])
async def list_projects(
    current_user: dict = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """List all projects for the current user"""
    # TODO: Implement project listing with database
    return []

@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get project details"""
    # TODO: Implement project retrieval with database
    raise HTTPException(status_code=404, detail="Project not found")

@app.put("/api/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update project"""
    # TODO: Implement project update with database
    raise HTTPException(status_code=404, detail="Project not found")

@app.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete project"""
    # TODO: Implement project deletion with database
    return {"message": "Project deleted successfully"}

# Task management endpoints
@app.post("/api/projects/{project_id}/tasks")
async def create_task(
    project_id: str,
    task: TaskCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new task for a project"""
    # TODO: Implement task creation with database
    task_id = str(uuid.uuid4())
    return {"id": task_id, "message": "Task created successfully"}

@app.get("/api/projects/{project_id}/tasks")
async def list_tasks(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List all tasks for a project"""
    # TODO: Implement task listing with database
    return []

# Agent Management endpoints
@app.get("/api/agents")
async def list_agents(current_user: dict = Depends(get_current_user)):
    """List all available agents and their capabilities"""
    try:
        capabilities = await deerflow_pm_integration.get_agent_capabilities()
        return {
            "success": True,
            "capabilities": capabilities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/chat")
async def chat_with_agents(
    message: str,
    project_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Chat with integrated agents (DeerFlow + PM Agents)"""
    try:
        result = await deerflow_pm_integration.process_request(
            user_input=message,
            user_id=current_user["user_id"],
            project_id=project_id
        )
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/create-project-with-research")
async def create_project_with_research(
    project_description: str,
    research_requirements: Optional[List[str]] = None,
    current_user: dict = Depends(get_current_user)
):
    """Create a project with integrated research"""
    try:
        result = await deerflow_pm_integration.create_project_with_research(
            project_description=project_description,
            user_id=current_user["user_id"],
            research_requirements=research_requirements
        )
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Research endpoints
@app.post("/api/research")
async def start_research(
    topic: str,
    project_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Start a research session using DeerFlow"""
    try:
        result = await deerflow_pm_integration.process_request(
            user_input=f"Research: {topic}",
            user_id=current_user["user_id"],
            project_id=project_id
        )
        return {
            "success": True,
            "research_id": str(uuid.uuid4()),
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/research/{research_id}")
async def get_research_results(
    research_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get research results"""
    # TODO: Implement research results retrieval from database
    return {
        "research_id": research_id,
        "status": "completed",
        "message": "Research results will be stored in database"
    }

# Knowledge base endpoints
@app.post("/api/knowledge/search")
async def search_knowledge(
    query: str,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Search the knowledge base"""
    # TODO: Implement vector search
    return {"query": query, "results": []}

# Analytics endpoints
@app.get("/api/analytics/projects/{project_id}/metrics")
async def get_project_metrics(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get project metrics and analytics"""
    # TODO: Implement metrics calculation
    return {"project_id": project_id, "metrics": {}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
