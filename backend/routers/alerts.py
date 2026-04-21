"""
Alert management endpoints.
POST /alerts/send - Generate and dispatch alert
POST /alerts/at-delivery - Africa's Talking delivery webhook
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from core.database import get_session
from core.security import get_current_user, TokenPayload
from models.orm import AlertLog
from schemas.api import SendAlertRequest, AlertDispatchResponse, AfricasTalkingWebhookPayload
from services.tasks.alert_task import dispatch_alert
from utils.alerts import hash_phone_number

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/send", response_model=AlertDispatchResponse)
async def send_alert(
    request: SendAlertRequest,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> AlertDispatchResponse:
    """
    Manually dispatch alert for county.
    
    Generates SMS/USSD based on latest risk snapshot + SHAP explanations.
    Dispatches via Africa's Talking.
    
    Only authenticated users can trigger alerts.
    """
    from models.orm import RiskSnapshot, County
    from sqlalchemy import select
    
    # Find county
    county_result = await db.execute(
        select(County).where(County.code == request.county_code)
    )
    county = county_result.scalar_one_or_none()
    
    if not county:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"County {request.county_code} not found",
        )
    
    # Get latest risk snapshot
    risk_result = await db.execute(
        select(RiskSnapshot)
        .where(RiskSnapshot.county_id == county.id)
        .order_by(RiskSnapshot.timestamp.desc())
        .limit(1)
    )
    snapshot = risk_result.scalar_one_or_none()
    
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No risk data for {county.name}",
        )
    
    # Dispatch alert asynchronously via Celery
    task = dispatch_alert.delay(
        county_code=request.county_code,
        phone_number=request.phone_number,
        language=request.language,
        include_shap=request.include_shap,
    )
    
    # Create placeholder alert log
    alert_log = AlertLog(
        county_code=request.county_code,
        channel="sms",
        phone_number_hash=hash_phone_number(request.phone_number),
        message_body="[pending dispatch]",
        alert_level="Medium",
        sent_at=datetime.now(timezone.utc),
        delivery_status="pending",
    )
    
    db.add(alert_log)
    await db.commit()
    await db.refresh(alert_log)
    
    logger.info(
        f"Alert dispatch job queued for {request.county_code} "
        f"(task_id: {task.id})"
    )
    
    return AlertDispatchResponse(
        alert_id=alert_log.id,
        county_code=request.county_code,
        channel="sms",
        sent_at=datetime.now(timezone.utc),
        delivery_status="pending",
    )


@router.post("/at-delivery")
async def receive_delivery_report(
    payload: AfricasTalkingWebhookPayload,
    db: AsyncSession = Depends(get_session),
):
    """
    Webhook endpoint for Africa's Talking delivery reports.
    
    Updates alert_logs table with delivery status.
    Called by Africa's Talking after SMS/USSD is delivered or failed.
    """
    try:
        phone_hash = hash_phone_number(payload.phoneNumber)
        
        # Update alert log with delivery status
        from sqlalchemy import update
        from models.orm import AlertLog
        
        stmt = (
            update(AlertLog)
            .where(AlertLog.phone_number_hash == phone_hash)
            .values(
                delivery_status=payload.status.lower(),
                delivery_timestamp=datetime.now(timezone.utc),
            )
        )
        
        result = await db.execute(stmt)
        await db.commit()
        
        logger.info(
            f"Updated delivery status for {payload.phoneNumber}: {payload.status}"
        )
        
        return {"status": "received"}
    
    except Exception as e:
        logger.error(f"Error processing delivery report: {e}")
        return {"status": "error", "message": str(e)}
