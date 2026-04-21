"""
WebSocket endpoint for real-time risk updates.
WS /ws/live - Subscribe to county or national risk updates via Redis pub/sub.
"""

import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Set

from core.security import get_current_user, TokenPayload
from core.redis_client import redis_pubsub_context, get_redis_cache

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Store active WebSocket connections per channel
active_connections: dict[str, Set[WebSocket]] = {}


@router.websocket("/ws/live")
async def websocket_endpoint(
    websocket: WebSocket,
    county_code: str | None = Query(None),
):
    """
    WebSocket endpoint for real-time risk updates.
    
    Query Params:
    - county_code: "01" to "47" for county-specific updates
                  omit for national updates
    
    Messages are streamed from Redis pub/sub:
    - "risk:{county_code}" - county-level risk snapshots
    - "alerts:national" - national-level alerts
    
    Front-end subscribes on page load, receives updates every 30 min (or on alert).
    Used by Mapbox frontend to update heatmap and markers in real-time.
    """
    await websocket.accept()
    
    # Determine subscription channel
    if county_code:
        channel = f"risk:{county_code}"
    else:
        channel = "alerts:national"
    
    # Add to active connections
    if channel not in active_connections:
        active_connections[channel] = set()
    active_connections[channel].add(websocket)
    
    logger.info(f"WebSocket client connected to {channel}")
    
    try:
        redis_client = get_redis_cache()
        
        # Subscribe to Redis channel
        pubsub = await redis_client.pubsub()
        await pubsub.subscribe(channel)
        
        # Listen for messages
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await websocket.send_json(data)
                except json.JSONDecodeError:
                    # Try sending raw string if not JSON
                    await websocket.send_text(message["data"])
        
        await pubsub.unsubscribe(channel)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from {channel}")
        active_connections[channel].discard(websocket)
    
    except Exception as e:
        logger.error(f"WebSocket error on {channel}: {e}")
        active_connections[channel].discard(websocket)
    
    finally:
        # Cleanup
        if channel in active_connections:
            active_connections[channel].discard(websocket)
            if len(active_connections[channel]) == 0:
                del active_connections[channel]
