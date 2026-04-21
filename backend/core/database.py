"""
SQLAlchemy 2.0 async database engine with PostGIS support.
Implements connection pooling, echo, and proper lifespan management.

Design decisions:
- AsyncPG driver for non-blocking I/O
- Pool sizing: 10 min / 20 max for typical load
- Use GeoAlchemy2 for PostGIS geometry columns
- Session factory for lazy connection acquisition
- Lifespan context manager to dispose engine on shutdown
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.orm import declarative_base
from sqlalchemy import event, Engine
from contextlib import asynccontextmanager
from core.config import settings
import logging

logger = logging.getLogger(__name__)

# Base class for all ORM models
Base = declarative_base()


def get_engine():
    """Create AsyncEngine with production settings."""
    # NullPool in production to avoid connection starvation
    # QueuePool in dev for better debugging
    pool_class = NullPool if settings.is_production() else QueuePool
    
    engine = create_async_engine(
        url=settings.database_url,
        echo=settings.sqlalchemy_echo,
        pool_pre_ping=True,  # Test connection before using
        pool_class=pool_class,
        pool_size=10 if settings.is_production() else 5,
        max_overflow=20 if settings.is_production() else 10,
        connect_args={
            "timeout": 10,
            "command_timeout": 10,
            "server_settings": {
                "jit": "off",  # Disable JIT for predictable performance
            },
        },
    )
    
    return engine


def get_session_factory(engine):
    """Create SessionMaker for async sessions."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


# Global engine & factory (initialized in lifespan context)
_engine = None
_session_factory = None


async def init_db():
    """Initialize database engine (called in lifespan startup)."""
    global _engine, _session_factory
    
    _engine = get_engine()
    _session_factory = get_session_factory(_engine)
    
    # Test connectivity
    try:
        async with _engine.begin() as conn:
            await conn.execute("SELECT 1")
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


async def close_db():
    """Close database engine (called in lifespan shutdown)."""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("Database connection closed")


async def get_session() -> AsyncSession:
    """Dependency injection for async database sessions."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Check lifespan context.")
    
    async with _session_factory() as session:
        yield session


@asynccontextmanager
async def get_db_context():
    """Context manager for manual session management (used in tasks/services)."""
    global _session_factory
    if _session_factory is None:
        raise RuntimeError("Database not initialized")
    
    async with _session_factory() as session:
        yield session
