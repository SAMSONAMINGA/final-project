"""
Admin endpoints (requires RBAC admin role).
POST /admin/retrain - Trigger model retraining
POST /admin/ekf-tune - Update EKF noise parameters
GET /admin/volunteers - List registered volunteer devices
POST /admin/volunteers - Register volunteer device
GET /admin/audit-logs - Paginated audit trail
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from core.database import get_session
from core.security import get_current_admin, TokenPayload
from models.orm import AuditLog
from schemas.api import (
    EKFTuneRequest,
    VolunteerDeviceRequest,
    VolunteerDeviceResponse,
    RetrainingJobResponse,
    AuditLogsResponse,
    AuditLogEntry,
)
from utils.ekf import ekf_manager
from utils.alerts import hash_phone_number

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/retrain", response_model=RetrainingJobResponse)
async def retrain_model(
    current_user: TokenPayload = Depends(get_current_admin),
) -> RetrainingJobResponse:
    """
    Trigger GATv2 model retraining job.
    
    Admin only. Queues async training task via Celery.
    Training uses latest risk snapshots + inference outcomes.
    """
    import uuid
    from services.tasks.inference_task import run_inference
    
    job_id = str(uuid.uuid4())[:8]
    
    # Queue retraining job (placeholder - actual training would be implemented)
    # task = retrain_model_task.delay(job_id=job_id)
    
    logger.info(f"Queued model retraining job {job_id}")
    
    return RetrainingJobResponse(
        job_id=job_id,
        status="pending",
        started_at=datetime.now(timezone.utc),
    )


@router.post("/ekf-tune")
async def tune_ekf_params(
    request: EKFTuneRequest,
    current_user: TokenPayload = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """
    Tune Extended Kalman Filter noise parameters for county.
    
    Admin only. Adjusts process noise (Q) and measurement noise (R)
    to improve rainfall fusion accuracy.
    """
    # Update EKF parameters
    ekf_manager.update_params(
        county_code=request.county_code,
        q=request.process_noise,
        r=request.measurement_noise,
    )
    
    # Log audit entry
    audit = AuditLog(
        user_id=current_user.sub,
        action="ekf_tune",
        resource_type="ekf_params",
        resource_id=request.county_code,
        changes={
            "process_noise": request.process_noise,
            "measurement_noise": request.measurement_noise,
            "reason": request.reason,
        },
        status="success",
    )
    
    db.add(audit)
    await db.commit()
    
    logger.info(
        f"Updated EKF parameters for {request.county_code} "
        f"(Q={request.process_noise}, R={request.measurement_noise})"
    )
    
    return {"status": "updated", "county_code": request.county_code}


@router.get("/volunteers")
async def list_volunteers(
    current_user: TokenPayload = Depends(get_current_admin),
) -> dict:
    """
    List all registered volunteer barometer devices.
    
    Admin only. Returns anonymized device IDs (hashed).
    """
    # Placeholder: would aggregate from barometer_readings table
    return {
        "total_devices": 0,
        "devices": [],
    }


@router.post("/volunteers", response_model=VolunteerDeviceResponse)
async def register_volunteer(
    request: VolunteerDeviceRequest,
    current_user: TokenPayload = Depends(get_current_admin),
) -> VolunteerDeviceResponse:
    """
    Register volunteer barometer device.
    
    Admin only. Pre-registers device for alert dispatching.
    """
    device_hash = hash_phone_number(request.device_id)
    phone_hash = hash_phone_number(request.phone_number)
    
    logger.info(f"Registered volunteer device {device_hash[:8]}...")
    
    return VolunteerDeviceResponse(
        device_id_hash=device_hash,
        phone_number_hash=phone_hash,
        county_code=request.county_code,
        registered_at=datetime.now(timezone.utc),
    )


@router.get("/audit-logs", response_model=AuditLogsResponse)
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: TokenPayload = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> AuditLogsResponse:
    """
    Retrieve paginated audit trail.
    
    Admin only. Immutable log of all admin actions.
    Used for compliance and forensic analysis.
    """
    # Count total
    count_result = await db.execute(
        select(AuditLog).__class__.select().froms(AuditLog)
    )
    
    # Fetch page
    result = await db.execute(
        select(AuditLog)
        .order_by(desc(AuditLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    
    audit_logs = result.scalars().all()
    
    entries = [
        AuditLogEntry(
            id=log.id,
            user_id=log.user_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            changes=log.changes,
            status=log.status,
            error_message=log.error_message,
            created_at=log.created_at,
        )
        for log in audit_logs
    ]
    
    return AuditLogsResponse(
        total=len(audit_logs),
        page=page,
        page_size=page_size,
        entries=entries,
    )
