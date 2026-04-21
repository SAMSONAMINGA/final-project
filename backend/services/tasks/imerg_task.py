"""
IMERG data fetch task (30-min cadence).
Fetches latest NASA GPM-IMERG Early Run snapshot and stores in database.
"""

import logging
from datetime import datetime, timezone
from sqlalchemy import select, and_

from services.celery_app import celery_app
from core.database import get_db_context
from models.orm import IMERGSnapshot
from utils.imerg_fetcher import get_imerg_latest

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # Retry after 1 minute
    name="services.tasks.imerg_task.fetch_imerg",
)
async def fetch_imerg(self):
    """
    Fetch latest IMERG data and store in database.
    
    Called via Celery Beat every 30 minutes.
    """
    try:
        # Fetch from NASA
        data = await get_imerg_latest()
        
        if not data:
            logger.warning("No IMERG data retrieved")
            return
        
        # Store in database
        async with get_db_context() as db:
            try:
                # Check if snapshot exists for this timestamp
                timestamp = datetime.fromisoformat(data["timestamp"]).replace(tzinfo=timezone.utc)
                
                existing = await db.execute(
                    select(IMERGSnapshot).where(IMERGSnapshot.timestamp == timestamp)
                )
                
                if existing.scalar_one_or_none():
                    logger.info(f"IMERG snapshot already exists for {timestamp}")
                    return
                
                # Create new snapshot
                snapshot = IMERGSnapshot(
                    timestamp=timestamp,
                    grid_json=data.get("grid"),
                    source_url=data.get("source_url"),
                )
                
                db.add(snapshot)
                await db.commit()
                
                logger.info(f"Stored IMERG snapshot for {timestamp}")
            
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to store IMERG snapshot: {e}")
                raise
    
    except Exception as exc:
        logger.error(f"IMERG fetch task failed: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
