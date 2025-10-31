"""
FastAPI server for Project Management Agent

This module provides RESTful APIs and WebSocket endpoints for the project management system.
"""

import logging
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, AsyncIterator
import asyncio
import json
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

from src.conversation.flow_manager import ConversationFlowManager
from src.workflow import run_agent_workflow_stream
from database.models import (
    Project, ProjectCreate, ProjectUpdate, 
    Task, TaskCreate, TaskUpdate,
    User, UserCreate
)
from database.connection import get_db_session
from database import crud as db_crud
from sqlalchemy.orm import Session

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

# Initialize conversation flow manager (will be initialized with DB session)
# Use a simple instance per request for now
flow_manager = ConversationFlowManager()

def get_flow_manager(db: Session = Depends(get_db_session)) -> ConversationFlowManager:
    """Get flow manager with database session"""
    # Create a new instance each time to ensure fresh db session
    fm = ConversationFlowManager(db_session=db)
    return fm

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    from database import init_db
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️  Database initialization warning: {e}")

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
    # For now, return a mock user with a valid UUID
    # This should match the user created in setup_test_data.py
    return {"user_id": "f430f348-d65f-427f-9379-3d0f163393d1", "email": "user@example.com"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Config endpoint for DeerFlow UI compatibility
@app.get("/api/config")
async def get_config():
    """Return default config to prevent 404 errors"""
    return {
        "rag": {"provider": ""},
        "models": {
            "basic": [],
            "reasoning": []
        }
    }

# Chat endpoints
@app.post("/api/chat", response_model=ChatResponse)
async def send_message(
    message: ChatMessage,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Send a message to the conversation flow manager"""
    try:
        # Get flow manager with db session
        fm = get_flow_manager(db)
        response = await fm.process_message(
            message=message.message,
            session_id=message.session_id,
            user_id=current_user.get("user_id")
        )
        return ChatResponse(**response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Streaming chat endpoint for DeerFlow-style frontend
@app.post("/api/chat/stream")
async def chat_stream(request: Request, db: Session = Depends(get_db_session)):
    """Stream chat responses using Server-Sent Events (SSE)"""
    try:
        body = await request.json()
        user_message = body.get("messages", [{}])[0].get("content", "")
        thread_id = body.get("thread_id", str(uuid.uuid4()))
        
        # Get flow manager with db session
        fm = get_flow_manager(db)
        
        async def generate_stream() -> AsyncIterator[str]:
            """Generate SSE stream of chat responses with progress updates"""
            try:
                # First, generate PM plan to check if CREATE_WBS is needed
                # This is fast (one LLM call) and tells us if we need DeerFlow research
                temp_context = fm._get_or_create_context(thread_id)
                pm_plan = await fm.generate_pm_plan(user_message, temp_context)
                
                # Check if plan has CREATE_WBS steps that need research
                needs_research = False
                if pm_plan and pm_plan.get('steps'):
                    for step in pm_plan.get('steps', []):
                        if step.get('step_type') == 'create_wbs':
                            needs_research = True
                            break
                
                # For research queries, stream DeerFlow updates
                if needs_research:
                    # Yield initial message
                    initial_chunk = {
                        "id": str(uuid.uuid4()),
                        "thread_id": thread_id,
                        "agent": "coordinator",
                        "role": "assistant",
                        "content": "🦌 **Starting DeerFlow research...**\n\n",
                        "finish_reason": None
                    }
                    yield "event: message_chunk\n"
                    yield f"data: {json.dumps(initial_chunk)}\n\n"
                    
                    # Stream DeerFlow research progress
                    try:
                        # Extract project info for research query
                        project_name = ""
                        if "create wbs" in user_message.lower():
                            # Try to extract project name from message
                            parts = user_message.lower().split("wbs")
                            if len(parts) > 1:
                                remaining = parts[1].strip().split()
                                if remaining:
                                    # Get first few words as project name
                                    project_name = " ".join(remaining[:3]).replace("and", "").strip()
                        
                        research_query = f"Research typical phases, deliverables, and tasks for {project_name or 'this type of project'}. Focus on project structure and common components."
                        
                        # Call streaming workflow
                        research_chunk = {
                            "id": str(uuid.uuid4()),
                            "thread_id": thread_id,
                            "agent": "coordinator",
                            "role": "assistant",
                            "content": "🔍 Researching project structure and best practices...\n\n",
                            "finish_reason": None
                        }
                        yield "event: message_chunk\n"
                        yield f"data: {json.dumps(research_chunk)}\n\n"
                        
                        # Stream intermediate states from DeerFlow
                        last_step_emitted = ""
                        final_research_state = None
                        async for state in run_agent_workflow_stream(
                            user_input=research_query,
                            max_plan_iterations=1,
                            max_step_num=3,
                            enable_background_investigation=True,
                            enable_clarification=False
                        ):
                            # Store final state for later use
                            final_research_state = state
                            
                            # Extract progress information from state
                            if isinstance(state, dict):
                                # Check for current plan
                                current_plan = state.get("current_plan")
                                if current_plan:
                                    # Handle different plan types
                                    from src.prompts.planner_model import Plan
                                    
                                    if isinstance(current_plan, Plan):
                                        # Pydantic Plan model
                                        plan_title = current_plan.title
                                    elif isinstance(current_plan, dict):
                                        # Dict
                                        plan_title = current_plan.get("title", "")
                                    elif isinstance(current_plan, str):
                                        # String - skip it to avoid the .title() method issue
                                        continue
                                    else:
                                        # Unknown type - convert to string
                                        plan_title = str(current_plan)
                                    
                                    if plan_title and plan_title != last_step_emitted:
                                        progress_msg = f"📋 Planning: {plan_title}\n\n"
                                        progress_chunk = {
                                            "id": str(uuid.uuid4()),
                                            "thread_id": thread_id,
                                            "agent": "coordinator",
                                            "role": "assistant",
                                            "content": progress_msg,
                                            "finish_reason": None
                                        }
                                        yield "event: message_chunk\n"
                                        yield f"data: {json.dumps(progress_chunk)}\n\n"
                                        last_step_emitted = plan_title
                                
                                # Check for messages with agent names
                                messages = state.get("messages", [])
                                if messages:
                                    last_msg = messages[-1]
                                    if isinstance(last_msg, dict):
                                        agent_name = last_msg.get("name", "")
                                        content = last_msg.get("content", "")
                                        if agent_name and agent_name not in ["planner", "reporter"] and len(content) > 50:
                                            step_msg = f"⚙️ {agent_name.capitalize()} agent working...\n\n"
                                            step_chunk = {
                                                "id": str(uuid.uuid4()),
                                                "thread_id": thread_id,
                                                "agent": "coordinator",
                                                "role": "assistant",
                                                "content": step_msg,
                                                "finish_reason": None
                                            }
                                            yield "event: message_chunk\n"
                                            yield f"data: {json.dumps(step_chunk)}\n\n"
                        
                        # Store research result in context to avoid re-running
                        if final_research_state and isinstance(final_research_state, dict):
                            # Get or create context
                            from src.conversation.flow_manager import ConversationContext, FlowState, IntentType
                            
                            # Get context for this session
                            if thread_id not in fm.contexts:
                                fm.contexts[thread_id] = ConversationContext(
                                    session_id=thread_id,
                                    current_state=FlowState.INTENT_DETECTION,
                                    intent=IntentType.UNKNOWN,
                                    gathered_data={},
                                    required_fields=[],
                                    conversation_history=[],
                                    created_at=datetime.now(),
                                    updated_at=datetime.now()
                                )
                            
                            # Extract research results
                            context = fm.contexts[thread_id]
                            research_result = ""
                            if "final_report" in final_research_state:
                                research_result = final_research_state["final_report"]
                            elif "messages" in final_research_state:
                                messages = final_research_state["messages"]
                                if messages:
                                    last_msg = messages[-1]
                                    if isinstance(last_msg, dict):
                                        research_result = last_msg.get("content", "")
                            
                            # Store in gathered_data to skip re-research in process_message
                            if research_result:
                                context.gathered_data['research_context'] = research_result
                                context.gathered_data['research_already_done'] = True
                                logger.info(f"Stored research result in context for session {thread_id}")
                        
                        # Emit completion message
                        complete_chunk = {
                            "id": str(uuid.uuid4()),
                            "thread_id": thread_id,
                            "agent": "coordinator",
                            "role": "assistant",
                            "content": "✅ Research completed!\n\n",
                            "finish_reason": None
                        }
                        yield "event: message_chunk\n"
                        yield f"data: {json.dumps(complete_chunk)}\n\n"
                        
                    except Exception as research_error:
                        logger.error(f"DeerFlow streaming failed: {research_error}")
                        # Continue with normal flow even if streaming fails
                
                # Create a queue to collect streaming chunks
                stream_queue = asyncio.Queue()
                stream_done = False
                
                async def stream_callback(content: str):
                    """Callback to capture streaming chunks"""
                    await stream_queue.put(content)
                
                # Process message in background with streaming
                async def process_with_streaming():
                    nonlocal stream_done
                    try:
                        response = await fm.process_message(
                            message=user_message,
                            session_id=thread_id,
                            user_id="f430f348-d65f-427f-9379-3d0f163393d1",  # Mock user
                            stream_callback=stream_callback
                        )
                        # Put a sentinel to signal completion
                        await stream_queue.put(None)
                        return response
                    except Exception as e:
                        logger.error(f"Error in process_message: {e}")
                        await stream_queue.put(None)
                        return None
                
                # Start processing in background
                process_task = asyncio.create_task(process_with_streaming())
                
                # Stream chunks as they arrive
                while True:
                    try:
                        # Wait for chunk with timeout
                        chunk = await asyncio.wait_for(stream_queue.get(), timeout=1.0)
                        
                        if chunk is None:  # Sentinel - done
                            break
                        
                        # Yield chunk immediately
                        chunk_data = {
                            "id": str(uuid.uuid4()),
                            "thread_id": thread_id,
                            "agent": "coordinator",
                            "role": "assistant",
                            "content": chunk,
                            "finish_reason": None
                        }
                        yield "event: message_chunk\n"
                        yield f"data: {json.dumps(chunk_data)}\n\n"
                        
                    except asyncio.TimeoutError:
                        # Check if task is done
                        if process_task.done():
                            break
                        continue
                
                # Get final response
                response = await process_task
                if response:
                    response_message = response.get('message', '')
                    response_state = response.get('state', 'complete')
                    
                    finish_reason = None
                    if response_state == 'complete':
                        finish_reason = "stop"
                    elif '?' in response_message or 'specify' in response_message.lower():
                        finish_reason = "interrupt"
                else:
                    finish_reason = "stop"
                    response_message = ""
                    
                # Yield final chunk with finish reason
                chunk_data = {
                    "id": str(uuid.uuid4()),
                    "thread_id": thread_id,
                    "agent": "coordinator",
                    "role": "assistant",
                    "content": "",
                    "finish_reason": finish_reason
                }
                yield "event: message_chunk\n"
                yield f"data: {json.dumps(chunk_data)}\n\n"
                
            except Exception as e:
                # Yield error as message chunk
                error_message = f"Error: {str(e)}"
                error_data = {
                    "id": str(uuid.uuid4()),
                    "thread_id": thread_id,
                    "agent": "coordinator",
                    "role": "assistant",
                    "content": error_message,
                    "finish_reason": "stop"
                }
                yield "event: message_chunk\n"
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history/{session_id}")
async def get_chat_history(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get chat history for a session"""
    fm = get_flow_manager(db)
    if session_id in fm.contexts:
        context = fm.contexts[session_id]
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
    # Note: WebSocket can't use Depends, so we'll need to create flow manager here
    # For now, using a simple approach without db session in websocket
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process message through flow manager (without db session in websocket)
            # TODO: Get db session in websocket context
            global flow_manager
            if flow_manager is None:
                from database.connection import SessionLocal
                db = SessionLocal()
                flow_manager = ConversationFlowManager(db_session=db)
            
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
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create a new project"""
    try:
        # Create project using CRUD
        new_project = db_crud.create_project(
            db=db,
            name=project.name,
            description=project.description,
            created_by=current_user.get("user_id"),  # Convert from string to UUID if needed
            domain=project.domain,
            priority=project.priority,
            timeline_weeks=project.timeline_weeks,
            budget=project.budget
        )
        
        return ProjectResponse(
            id=str(new_project.id),
            name=new_project.name,
            description=new_project.description,
            status=new_project.status,
            created_at=new_project.created_at,
            updated_at=new_project.updated_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects", response_model=List[ProjectResponse])
async def list_projects(
    current_user: dict = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session)
):
    """List all projects for the current user"""
    try:
        projects = db_crud.get_projects(
            db=db,
            skip=skip,
            limit=limit,
            user_id=current_user.get("user_id")
        )
        
        return [
            ProjectResponse(
                id=str(p.id),
                name=p.name,
                description=p.description,
                status=p.status,
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in projects
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get project details"""
    try:
        from uuid import UUID
        project = db_crud.get_project(db, UUID(project_id))
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update project"""
    try:
        from uuid import UUID
        # Convert Pydantic model to dict and filter None values
        update_data = {k: v for k, v in project_update.dict().items() if v is not None}
        
        project = db_crud.update_project(db, UUID(project_id), **update_data)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Delete project"""
    try:
        from uuid import UUID
        success = db_crud.delete_project(db, UUID(project_id))
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"message": "Project deleted successfully"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Task management endpoints
@app.post("/api/projects/{project_id}/tasks")
async def create_task(
    project_id: str,
    task: TaskCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create a new task for a project"""
    try:
        from uuid import UUID
        new_task = db_crud.create_task(
            db=db,
            project_id=UUID(project_id),
            title=task.title,
            description=task.description,
            priority=task.priority,
            estimated_hours=task.estimated_hours,
            due_date=task.due_date,
            assigned_to=task.assigned_to,
            parent_task_id=task.parent_task_id
        )
        return {"id": str(new_task.id), "message": "Task created successfully"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}/tasks")
async def list_tasks(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """List all tasks for a project"""
    try:
        from uuid import UUID
        tasks = db_crud.get_tasks_by_project(db, UUID(project_id))
        return [
            {
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
                "estimated_hours": t.estimated_hours,
                "actual_hours": t.actual_hours,
                "due_date": t.due_date.isoformat() if t.due_date else None
            }
            for t in tasks
        ]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Sprint management endpoints
@app.get("/api/projects/{project_id}/sprints")
async def list_sprints(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """List all sprints for a project"""
    try:
        from uuid import UUID
        from database.orm_models import Sprint
        
        sprints = db.query(Sprint).filter(Sprint.project_id == UUID(project_id)).all()
        
        return [
            {
                "id": str(s.id),
                "name": s.name,
                "start_date": s.start_date.isoformat() if s.start_date else None,
                "end_date": s.end_date.isoformat() if s.end_date else None,
                "duration_weeks": s.duration_weeks,
                "duration_days": s.duration_days,
                "capacity_hours": s.capacity_hours,
                "planned_hours": s.planned_hours,
                "utilization": s.utilization,
                "status": s.status
            }
            for s in sprints
        ]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sprints/{sprint_id}/tasks")
async def get_sprint_tasks(
    sprint_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get all tasks in a sprint"""
    try:
        from uuid import UUID
        from database.orm_models import SprintTask
        
        sprint_tasks = db.query(SprintTask).filter(SprintTask.sprint_id == UUID(sprint_id)).all()
        
        tasks = []
        for st in sprint_tasks:
            # Get the task details
            from database.orm_models import Task
            task = db.query(Task).filter(Task.id == st.task_id).first()
            if task:
                tasks.append({
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "estimated_hours": task.estimated_hours,
                    "priority": task.priority,
                    "assigned_to": st.assigned_to_name,
                    "capacity_used": st.capacity_used
                })
        
        return tasks
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid sprint ID format")
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
    # TODO: Integrate with DeerFlow
    research_id = str(uuid.uuid4())
    return {
        "research_id": research_id,
        "status": "started",
        "message": "Research session started"
    }

@app.get("/api/research/{research_id}")
async def get_research_results(
    research_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get research results"""
    # TODO: Implement research results retrieval
    return {"research_id": research_id, "status": "completed", "results": []}

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

# Intent feedback endpoint for self-learning
@app.post("/api/intent/feedback")
async def record_intent_feedback(
    feedback: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Record user feedback on intent classification for self-learning"""
    try:
        classification_id = feedback.get("classification_id")
        feedback_type = feedback.get("feedback_type", "correction")  # correction, confirmation, improvement
        was_correct = feedback.get("was_correct")
        user_corrected_intent = feedback.get("user_corrected_intent")
        user_comment = feedback.get("user_comment")
        
        if not classification_id:
            raise HTTPException(status_code=400, detail="classification_id is required")
        
        # Record feedback through flow manager
        fm = get_flow_manager(db)
        success = await fm.record_user_feedback(
            classification_id=classification_id,
            feedback_type=feedback_type,
            was_correct=was_correct,
            user_corrected_intent=user_corrected_intent,
            user_comment=user_comment
        )
        
        if success:
            return {"message": "Feedback recorded successfully", "success": True}
        else:
            raise HTTPException(status_code=500, detail="Failed to record feedback")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Get intent metrics endpoint
@app.get("/api/intent/metrics")
async def get_intent_metrics(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get intent classification performance metrics"""
    try:
        fm = get_flow_manager(db)
        if fm.self_learning:
            metrics = fm.self_learning.get_intent_metrics()
            return metrics
        else:
            return {"message": "Self-learning system not available", "intents": [], "total_intents": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
