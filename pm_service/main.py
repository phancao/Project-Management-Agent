# PM Service - Main Application
"""
FastAPI application for PM Service.
Provides a unified API for PM provider interactions.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pm_service.config import settings
from pm_service.database.connection import check_db_connection, init_db
from pm_service.routers import (
    projects_router,
    tasks_router,
    sprints_router,
    users_router,
    providers_router
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")
    init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down PM Service")


# Create FastAPI app
app = FastAPI(
    title=settings.service_name,
    version=settings.service_version,
    description="Unified API for Project Management provider interactions",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from pm_service.database import get_db_session
    from pm_service.handlers import PMHandler
    
    db_connected = check_db_connection()
    providers_count = 0
    
    if db_connected:
        try:
            db = next(get_db_session())
            handler = PMHandler(db)
            providers_count = len(handler.get_active_providers())
        except Exception as e:
            logger.error(f"Error getting providers count: {e}")
    
    return {
        "status": "healthy" if db_connected else "unhealthy",
        "version": settings.service_version,
        "providers_count": providers_count,
        "database_connected": db_connected
    }


# Include routers
app.include_router(projects_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(sprints_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(providers_router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "pm_service.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

