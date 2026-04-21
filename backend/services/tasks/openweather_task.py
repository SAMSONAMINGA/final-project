"""
OpenWeather data fetch task (30-min cadence).
Fetches current weather + forecast for all Kenya county centroids.
"""

import logging
from datetime import datetime, timezone
import asyncio

from services.celery_app import celery_app
from core.database import get_db_context
from models.orm import OpenWeatherSnapshot
from utils.imerg_fetcher import get_openweather_for_counties
from services.county_loader import county_loader

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="services.tasks.openweather_task.fetch_openweather",
)
async def fetch_openweather(self):
    """
    Fetch OpenWeather One Call 3.0 for all county centroids.
    
    Called via Celery Beat every 30 minutes.
    """
    try:
        # Get county centroids
        if not county_loader.is_loaded():
            logger.warning("County loader not initialized")
            return
        
        locations = county_loader.get_county_locations()
        
        # Fetch weather for all counties
        weather_data = await get_openweather_for_counties(locations)
        
        # Store in database
        async with get_db_context() as db:
            try:
                timestamp = datetime.now(timezone.utc)
                stored_count = 0
                
                for county_code, data in weather_data.items():
                    if not data:
                        logger.warning(f"No OpenWeather data for {county_code}")
                        continue
                    
                    # Get county from database
                    from sqlalchemy import select
                    from models.orm import County
                    
                    result = await db.execute(
                        select(County).filter(County.code == county_code)
                    )
                    county = result.scalar_one_or_none()
                    
                    if not county:
                        logger.warning(f"County {county_code} not found")
                        continue
                    
                    # Create snapshot
                    snapshot = OpenWeatherSnapshot(
                        county_id=county.id,
                        timestamp=timestamp,
                        data_json=data.get("full_response"),
                        current_precip_mm_h=data.get("current_precip_mm_h"),
                        forecast_precip_mm_h=data.get("forecast_precip_mm_h"),
                    )
                    
                    db.add(snapshot)
                    stored_count += 1
                
                await db.commit()
                logger.info(f"Stored OpenWeather snapshots for {stored_count} counties")
            
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to store OpenWeather snapshots: {e}")
                raise
    
    except Exception as exc:
        logger.error(f"OpenWeather fetch task failed: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
