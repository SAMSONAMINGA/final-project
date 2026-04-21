"""
FastAPI main application entry point.
Implements lifespan context manager for startup/shutdown.
Registers all routers, middleware, and exception handlers.

Design decisions:
- Lifespan context manager (FastAPI 0.93+) for clean startup/shutdown
- Initialize database, Redis, ML models before accepting requests
- CORS middleware with strict allowlist
- Rate limiting via slowapi
- Structured JSON logging via structlog
- Health check endpoint for orchestration
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from datetime import datetime, timezone
import structlog

from core.config import settings
from core.database import init_db, close_db
from core.redis_client import init_redis, close_redis
from services.ml_loader import model_manager
from services.county_loader import county_loader
from routers import auth, barometer, risk, simulate, websocket, alerts, admin
from schemas.api import HealthCheckResponse

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = logging.getLogger(__name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Runs on startup and cleanup on shutdown.
    """
    # ========== STARTUP ==========
    logger.info("=" * 60)
    logger.info("FloodGuard KE Backend - Starting up")
    logger.info("=" * 60)
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        await init_db()
        
        # Initialize Redis
        logger.info("Initializing Redis...")
        await init_redis()
        
        # Load ML models
        logger.info("Loading ML models...")
        model_manager.load_models()
        
        # Load county metadata
        logger.info("Loading county metadata...")
        from core.database import get_db_context
        async with get_db_context() as db:
            await county_loader.load_from_database(db)
        
        logger.info("✓ All systems initialized successfully")
        logger.info("=" * 60)
    
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield  # App runs here
    
    # ========== SHUTDOWN ==========
    logger.info("=" * 60)
    logger.info("FloodGuard KE Backend - Shutting down")
    logger.info("=" * 60)
    
    try:
        # Close database
        logger.info("Closing database...")
        await close_db()
        
        # Close Redis
        logger.info("Closing Redis...")
        await close_redis()
        
        logger.info("✓ Cleanup completed")
    
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Create FastAPI app
app = FastAPI(
    title="FloodGuard KE Backend",
    description="Nationwide Kenya hyperlocal flash-flood early warning system",
    version="1.0.0",
    lifespan=lifespan,
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware (strict allowlist)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(barometer.router)
app.include_router(risk.router)
app.include_router(simulate.router)
app.include_router(websocket.router)
app.include_router(alerts.router)
app.include_router(admin.router)


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    System health status endpoint.
    
    Used by container orchestration (Docker, Kubernetes) for liveness checks.
    Returns status of database, Redis, and ML models.
    """
    from core.database import _engine
    from core.redis_client import _redis_cache, _redis_broker
    
    components = {}
    is_healthy = True
    
    # Check database
    try:
        if _engine:
            async with _engine.begin() as conn:
                await conn.execute("SELECT 1")
            components["database"] = "ok"
        else:
            components["database"] = "not_initialized"
            is_healthy = False
    except Exception as e:
        components["database"] = f"error: {e}"
        is_healthy = False
    
    # Check Redis
    try:
        if _redis_cache:
            await _redis_cache.ping()
            components["redis"] = "ok"
        else:
            components["redis"] = "not_initialized"
            is_healthy = False
    except Exception as e:
        components["redis"] = f"error: {e}"
        is_healthy = False
    
    # Check ML models
    if model_manager.get_gatv2() is not None:
        components["ml_model"] = f"ok ({model_manager.get_version()})"
    else:
        components["ml_model"] = "not_loaded"
    
    # Check county data
    if county_loader.is_loaded():
        components["county_data"] = "ok"
    else:
        components["county_data"] = "not_loaded"
        is_healthy = False
    
    status_str = "healthy" if is_healthy else ("degraded" if components.get("ml_model") != "not_loaded" else "unhealthy")
    
    return HealthCheckResponse(
        status=status_str,
        timestamp=datetime.now(timezone.utc),
        components=components,
    )


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": "FloodGuard KE",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development(),
        log_level=settings.log_level.lower(),
    )
