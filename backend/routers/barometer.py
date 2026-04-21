"""
Barometer readings ingestion endpoints.
POST /ingest/barometer - single reading
POST /ingest/barometer/batch - up to 12 readings
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from geoalchemy2.functions import ST_GeomFromText

from core.database import get_session
from models.orm import BarometerReading, County
from schemas.api import (
    BarometerReading as BarometerReadingSchema,
    BarometerBatchRequest,
    BarometerReadingResponse,
)
from core.security import hash_device_id
from slowapi.util import get_remote_address
from slowapi import Limiter
import hashlib

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["barometer"])

# Rate limiter: 60 req/min on barometer endpoints
limiter = Limiter(key_func=get_remote_address)


async def get_county_by_point(lat: float, lon: float, db: AsyncSession) -> County:
    """
    Find county containing the point (spatial lookup).
    Uses PostGIS ST_Contains on county multipolygons.
    """
    from sqlalchemy import text
    
    # WKT point
    point_wkt = f"POINT({lon} {lat})"
    
    result = await db.execute(
        text(
            f"""
            SELECT id, code, name FROM counties
            WHERE ST_Contains(geometry, ST_GeomFromText(:point, 4326))
            LIMIT 1
            """
        ),
        {"point": point_wkt}
    )
    
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location outside Kenya boundaries",
        )
    
    # Fetch full county object
    from sqlalchemy import select
    county_result = await db.execute(
        select(County).where(County.id == row[0])
    )
    return county_result.scalar_one()


@router.post("/barometer", response_model=BarometerReadingResponse)
@limiter.limit("60/minute")
async def ingest_barometer_single(
    request: BarometerReadingSchema,
    db: AsyncSession = Depends(get_session),
) -> BarometerReadingResponse:
    """
    Ingest single barometer reading.
    
    Rate limit: 60 req/minute
    
    Returns confirmation with timestamp.
    """
    try:
        # Find county
        county = await get_county_by_point(request.latitude, request.longitude, db)
        
        # Create reading
        reading = BarometerReading(
            county_id=county.id,
            device_id_hash=hash_device_id(request.device_id),
            location=f"POINT({request.longitude} {request.latitude})",
            pressure_hpa=request.pressure_hpa,
            altitude_m=request.altitude_m,
            temperature_c=request.temperature_c,
            humidity_pct=request.humidity_pct,
            timestamp=request.timestamp,
        )
        
        db.add(reading)
        await db.commit()
        await db.refresh(reading)
        
        logger.info(f"Stored barometer reading for device {hash_device_id(request.device_id)[:8]}...")
        
        return BarometerReadingResponse(
            id=reading.id,
            timestamp=reading.timestamp,
            created_at=reading.created_at,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error ingesting barometer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest reading",
        )


@router.post("/barometer/batch", response_model=list[BarometerReadingResponse])
@limiter.limit("30/minute")
async def ingest_barometer_batch(
    request: BarometerBatchRequest,
    db: AsyncSession = Depends(get_session),
) -> list[BarometerReadingResponse]:
    """
    Ingest batch of up to 12 barometer readings.
    
    Rate limit: 30 req/minute
    
    More efficient than single endpoint for multiple readings.
    """
    responses = []
    
    for reading_schema in request.readings:
        try:
            county = await get_county_by_point(
                reading_schema.latitude,
                reading_schema.longitude,
                db
            )
            
            reading = BarometerReading(
                county_id=county.id,
                device_id_hash=hash_device_id(reading_schema.device_id),
                location=f"POINT({reading_schema.longitude} {reading_schema.latitude})",
                pressure_hpa=reading_schema.pressure_hpa,
                altitude_m=reading_schema.altitude_m,
                temperature_c=reading_schema.temperature_c,
                humidity_pct=reading_schema.humidity_pct,
                timestamp=reading_schema.timestamp,
            )
            
            db.add(reading)
            responses.append(
                BarometerReadingResponse(
                    id=0,  # Will be set after commit
                    timestamp=reading.timestamp,
                    created_at=datetime.now(),
                )
            )
        
        except HTTPException as e:
            logger.warning(f"Skipping invalid reading: {e.detail}")
            continue
    
    try:
        await db.commit()
        logger.info(f"Stored batch of {len(responses)} barometer readings")
        return responses
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Error storing batch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest batch",
        )
