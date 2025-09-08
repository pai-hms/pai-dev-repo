"""FastAPI main application following design principles."""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from webapp.dependencies import startup_event, shutdown_event
from webapp.routers import agent, data
from webapp.models import HealthResponse
from src.database.connection import db_manager
from src.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    await startup_event()
    yield
    # Shutdown
    await shutdown_event()


# Create FastAPI app
app = FastAPI(
    title="PAI SQL Agent",
    description="SQL Agent for Pohang City Budget and Census Data Analysis",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agent.router)
app.include_router(data.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "PAI SQL Agent API",
        "version": "0.1.0",
        "description": "SQL Agent for Pohang City Budget and Census Data Analysis",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        connection = await db_manager.get_connection()
        await db_manager.release_connection(connection)
        database_connected = True
    except Exception:
        database_connected = False
    
    # Check if agent is ready (simplified check)
    agent_ready = bool(settings.openai_api_key)
    
    status = "healthy" if database_connected and agent_ready else "unhealthy"
    
    return HealthResponse(
        status=status,
        timestamp=datetime.utcnow(),
        database_connected=database_connected,
        agent_ready=agent_ready,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "webapp.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
