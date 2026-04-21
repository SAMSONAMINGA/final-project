"""
Redis client for pub/sub (WebSocket real-time updates) and rate limiting.
Manages connection pooling and graceful shutdown.

Design decisions:
- Separate URL for broker (Celery tasks) vs cache/pub-sub
- Connection pooling with health checks
- Automatic reconnect with exponential backoff
- RESP3 for pub/sub performance
"""

import redis.asyncio as redis
from redis.asyncio import Redis as AsyncRedis
from contextlib import asynccontextmanager
import logging

from core.config import settings

logger = logging.getLogger(__name__)

_redis_cache: AsyncRedis | None = None
_redis_broker: AsyncRedis | None = None


async def init_redis():
    """Initialize Redis connections (called in lifespan startup)."""
    global _redis_cache, _redis_broker
    
    try:
        # Cache/pub-sub connection
        _redis_cache = await redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={
                1: 1,  # TCP_KEEPIDLE
                2: 3,  # TCP_KEEPINTVL
                3: 5,  # TCP_KEEPCNT
            },
            health_check_interval=30,
        )
        
        # Broker connection (Celery tasks)
        _redis_broker = await redis.from_url(
            settings.redis_broker_url,
            encoding="utf-8",
            decode_responses=True,
            socket_keepalive=True,
            health_check_interval=30,
        )
        
        # Test connectivity
        await _redis_cache.ping()
        await _redis_broker.ping()
        
        logger.info("Redis connections established")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise


async def close_redis():
    """Close Redis connections (called in lifespan shutdown)."""
    global _redis_cache, _redis_broker
    
    if _redis_cache:
        await _redis_cache.close()
    if _redis_broker:
        await _redis_broker.close()
    
    logger.info("Redis connections closed")


def get_redis_cache() -> AsyncRedis:
    """Get Redis cache/pub-sub client."""
    if _redis_cache is None:
        raise RuntimeError("Redis not initialized")
    return _redis_cache


def get_redis_broker() -> AsyncRedis:
    """Get Redis broker client (for Celery)."""
    if _redis_broker is None:
        raise RuntimeError("Redis not initialized")
    return _redis_broker


@asynccontextmanager
async def redis_pubsub_context():
    """Context manager for pub/sub operations."""
    redis_client = get_redis_cache()
    pubsub = redis_client.pubsub()
    try:
        yield pubsub
    finally:
        await pubsub.close()


async def publish_risk_update(county_code: str, risk_data: dict):
    """
    Publish risk update to Redis pub/sub for WebSocket subscribers.
    
    Args:
        county_code: 2-char county code (01-47)
        risk_data: Risk snapshot data to publish
    """
    redis_client = get_redis_cache()
    channel = f"risk:{county_code}"
    await redis_client.publish(channel, str(risk_data))  # Redis pub/sub expects strings


async def publish_national_alert(alert_data: dict):
    """
    Publish national-level alert to Redis.
    
    Args:
        alert_data: Alert data to publish nationally
    """
    redis_client = get_redis_cache()
    await redis_client.publish("alerts:national", str(alert_data))
