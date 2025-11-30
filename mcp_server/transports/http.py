"""
HTTP (REST API) Transport for PM MCP Server

Provides standard REST API endpoints for PM operations.
Uses PM Service for data operations.
"""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..config import PMServerConfig
from ..core.tool_context import ToolContext
from ..auth import AuthManager, AuthMiddleware

logger = logging.getLogger(__name__)


# Request/Response Models
class ToolCallRequest(BaseModel):
    """Request to call a tool."""
    tool: str = Field(..., description="Tool name to call")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolCallResponse(BaseModel):
    """Response from tool call."""
    tool: str
    result: Any
    success: bool
    error: str | None = None


class ToolInfo(BaseModel):
    """Tool information."""
    name: str
    description: str
    category: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ServerInfo(BaseModel):
    """Server information."""
    name: str
    version: str
    transport: str
    status: str
    tools_count: int
    providers_count: int


def create_http_app(
    context: ToolContext,
    config: PMServerConfig,
    enable_auth: bool = True
) -> FastAPI:
    """
    Create FastAPI application with HTTP REST API endpoints.
    
    Args:
        context: ToolContext instance
        config: Server configuration
        enable_auth: Enable authentication (default: True)
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="PM MCP Server API",
        description="Project Management MCP Server REST API with Authentication",
        version=config.server_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure based on config in production
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*", "Authorization"],
    )
    
    # Initialize authentication
    auth_manager = AuthManager()
    
    # Add authentication middleware if enabled
    if enable_auth:
        app.add_middleware(AuthMiddleware, auth_manager=auth_manager)
        logger.info("Authentication enabled")
    else:
        logger.warning("Authentication disabled - server is open to all!")
    
    # Store instances in app state
    app.state.context = context
    app.state.config = config
    app.state.auth_manager = auth_manager
    app.state.auth_enabled = enable_auth
    
    # Tool registry organized by category
    app.state.tools_by_category = {
        "projects": {},
        "tasks": {},
        "sprints": {},
        "epics": {},
        "users": {},
        "analytics": {},
        "task_interactions": {},
    }
    
    # Include authentication router
    if enable_auth:
        from ..auth.routes import create_auth_router
        auth_router = create_auth_router(auth_manager)
        app.include_router(auth_router)
        logger.info("Authentication routes registered")
    
    @app.get("/", response_model=ServerInfo)
    async def root():
        """Get server information."""
        providers = context.provider_manager.get_active_providers()
        total_tools = sum(
            len(tools) for tools in app.state.tools_by_category.values()
        )
        
        return ServerInfo(
            name=config.server_name,
            version=config.server_version,
            transport="http",
            status="running",
            tools_count=total_tools,
            providers_count=len(providers),
        )
    
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        try:
            providers = context.provider_manager.get_active_providers()
            total_tools = sum(
                len(tools) for tools in app.state.tools_by_category.values()
            )
            
            return {
                "status": "healthy",
                "providers": len(providers),
                "tools": total_tools,
                "categories": list(app.state.tools_by_category.keys()),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=503, detail=f"Unhealthy: {str(e)}")
    
    @app.get("/tools", response_model=list[ToolInfo])
    async def list_tools(
        category: str | None = Query(None, description="Filter by category")
    ):
        """List all available tools, optionally filtered by category."""
        try:
            tools_list = []
            
            if category:
                if category not in app.state.tools_by_category:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Category '{category}' not found"
                    )
                tools = app.state.tools_by_category[category]
                for name, info in tools.items():
                    tools_list.append(ToolInfo(
                        name=name,
                        description=info.get("description", ""),
                        category=category,
                        parameters=info.get("parameters", {}),
                    ))
            else:
                for cat, tools in app.state.tools_by_category.items():
                    for name, info in tools.items():
                        tools_list.append(ToolInfo(
                            name=name,
                            description=info.get("description", ""),
                            category=cat,
                            parameters=info.get("parameters", {}),
                        ))
            
            return tools_list
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/tools/categories")
    async def list_categories():
        """List all tool categories with counts."""
        try:
            categories = {}
            for cat, tools in app.state.tools_by_category.items():
                categories[cat] = {
                    "name": cat,
                    "tool_count": len(tools),
                    "tools": list(tools.keys()),
                }
            
            return {
                "categories": categories,
                "total_categories": len(categories),
                "total_tools": sum(c["tool_count"] for c in categories.values()),
            }
        except Exception as e:
            logger.error(f"Error listing categories: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/tools/call", response_model=ToolCallResponse)
    async def call_tool(request: ToolCallRequest):
        """
        Call a tool with given arguments.
        
        This is the main endpoint for executing PM operations.
        """
        try:
            tool_name = request.tool
            arguments = request.arguments
            
            logger.info(f"HTTP tool call: {tool_name} with args: {arguments}")
            
            # Find tool in categories
            tool_func = None
            for category, tools in app.state.tools_by_category.items():
                if tool_name in tools:
                    tool_func = tools[tool_name]["function"]
                    break
            
            if not tool_func:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tool '{tool_name}' not found"
                )
            
            # Execute tool
            result = await tool_func(arguments)
            
            return ToolCallResponse(
                tool=tool_name,
                result=result,
                success=True,
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error calling tool {request.tool}: {e}", exc_info=True)
            return ToolCallResponse(
                tool=request.tool,
                result=None,
                success=False,
                error=str(e),
            )
    
    # ========== Project Endpoints (using PM Service) ==========
    
    @app.get("/projects")
    async def list_projects(
        provider_id: str | None = None,
        search: str | None = None,
        limit: int | None = None,
    ):
        """List all projects."""
        try:
            result = await context.pm_service.list_projects(
                provider_id=provider_id,
                limit=limit or 100
            )
            projects = result.get("items", [])
            
            if search:
                search_lower = search.lower()
                projects = [
                    p for p in projects
                    if search_lower in p.get("name", "").lower()
                    or search_lower in p.get("description", "").lower()
                ]
            
            return {"projects": projects, "count": len(projects)}
        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/projects/{project_id}")
    async def get_project(project_id: str):
        """Get project details."""
        try:
            project = await context.pm_service.get_project(project_id)
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            return project
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting project: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ========== Task Endpoints (using PM Service) ==========
    
    @app.get("/tasks/my")
    async def list_my_tasks(
        status: str | None = None,
        provider_id: str | None = None,
    ):
        """List current user's tasks."""
        try:
            result = await context.pm_service.list_tasks(
                status=status
            )
            tasks = result.get("items", [])
            
            # Apply provider_id filter if specified
            if provider_id:
                tasks = [t for t in tasks if t.get("provider_id") == provider_id]
            
            return {"tasks": tasks, "count": len(tasks)}
        except Exception as e:
            logger.error(f"Error listing my tasks: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/projects/{project_id}/tasks")
    async def list_project_tasks(
        project_id: str,
        status: str | None = None,
        assignee: str | None = None,
    ):
        """List tasks in a project."""
        try:
            result = await context.pm_service.list_tasks(
                project_id=project_id,
                status=status,
                assignee_id=assignee
            )
            tasks = result.get("items", [])
            return {"tasks": tasks, "count": len(tasks)}
        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/tasks/{task_id}")
    async def get_task(task_id: str):
        """Get task details."""
        try:
            task = await context.pm_service.get_task(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            return task
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ========== Sprint Endpoints (using PM Service) ==========
    
    @app.get("/projects/{project_id}/sprints")
    async def list_sprints(
        project_id: str,
        status: str | None = None,
    ):
        """List sprints in a project."""
        try:
            result = await context.pm_service.list_sprints(
                project_id=project_id,
                status=status
            )
            sprints = result.get("items", [])
            return {"sprints": sprints, "count": len(sprints)}
        except Exception as e:
            logger.error(f"Error listing sprints: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/sprints/{sprint_id}")
    async def get_sprint(sprint_id: str):
        """Get sprint details."""
        try:
            sprint = await context.pm_service.get_sprint(sprint_id)
            if not sprint:
                raise HTTPException(status_code=404, detail="Sprint not found")
            return sprint
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting sprint: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ========== User Endpoints (using PM Service) ==========
    
    @app.get("/users")
    async def list_users(
        project_id: str | None = None,
        provider_id: str | None = None,
    ):
        """List users."""
        try:
            result = await context.pm_service.list_users(
                project_id=project_id
            )
            users = result.get("items", [])
            return {"users": users, "count": len(users)}
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/users/me")
    async def get_current_user_endpoint(provider_id: str | None = None):
        """Get current user information."""
        try:
            # PM Service doesn't have a "me" endpoint yet
            # Return a placeholder or fetch from first provider
            result = await context.pm_service.list_users(limit=1)
            users = result.get("items", [])
            if not users:
                raise HTTPException(status_code=404, detail="User not found")
            return users[0]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ========== Analytics Endpoints ==========
    
    @app.get("/analytics/burndown/{sprint_id}")
    async def get_burndown_chart(sprint_id: str):
        """Get burndown chart data for a sprint."""
        try:
            raise HTTPException(
                status_code=501, 
                detail="Burndown chart is available via /api/analytics/projects/{project_id}/burndown endpoint. "
                       "Please use the analytics API endpoint instead."
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting burndown chart: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/analytics/velocity/{project_id}")
    async def get_velocity_chart(
        project_id: str,
        sprint_count: int = Query(5, description="Number of sprints to analyze")
    ):
        """Get velocity chart data for a project."""
        try:
            raise HTTPException(
                status_code=501,
                detail="Velocity chart is available via /api/analytics/projects/{project_id}/velocity endpoint. "
                       "Please use the analytics API endpoint instead."
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting velocity chart: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return app


def register_tool_with_http(
    app: FastAPI,
    category: str,
    tool_name: str,
    tool_func: Any,
    description: str = "",
    parameters: dict[str, Any] | None = None
):
    """
    Register a tool with the HTTP app.
    
    Args:
        app: FastAPI application
        category: Tool category
        tool_name: Name of the tool
        tool_func: Tool function (async callable)
        description: Tool description
        parameters: Tool parameters schema
    """
    if category not in app.state.tools_by_category:
        app.state.tools_by_category[category] = {}
    
    app.state.tools_by_category[category][tool_name] = {
        "function": tool_func,
        "description": description,
        "parameters": parameters or {},
    }
    logger.debug(f"Registered tool: {category}.{tool_name}")

