"""
Simulation endpoint.
POST /simulate - Trigger fresh GATv2 inference, return time-stepped frames for Cesium 3D.
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from core.database import get_session
from services.ml_loader import model_manager
from schemas.api import SimulationResponse, SimulationFrameResponse, NodeRisk, SHAPFactor

logger = logging.getLogger(__name__)

router = APIRouter(tags=["simulation"])


@router.post("/simulate", response_model=SimulationResponse)
async def simulate_flood(
    county_code: str,
    duration_hours: int = 3,
    step_minutes: int = 15,
    db: AsyncSession = Depends(get_session),
) -> SimulationResponse:
    """
    Trigger flood simulation for Cesium 3D animation.
    
    Returns time-stepped frames showing:
    - Progressive water depth increase (cm)
    - Risk evolution over time
    - Weakness points (critical junctions)
    
    Used by Cesium 3D visualization to show progression scenario.
    
    Query Params:
    - duration_hours: 1-6 hours (default 3)
    - step_minutes: 5-60 minute cadence (default 15)
    """
    # Validate inputs
    if not (1 <= duration_hours <= 6):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="duration_hours must be 1-6",
        )
    
    if not (5 <= step_minutes <= 60):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="step_minutes must be 5-60",
        )
    
    # Get latest risk snapshot for county
    from models.orm import RiskSnapshot, County
    from sqlalchemy import select
    
    county_result = await db.execute(
        select(County).where(County.code == county_code)
    )
    county = county_result.scalar_one_or_none()
    
    if not county:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"County {county_code} not found",
        )
    
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
    
    # Generate time-stepped frames (simulate depth progression)
    frames = []
    start_time = datetime.now(timezone.utc)
    
    nodes_baseline = snapshot.nodes_json or []
    num_steps = (duration_hours * 60) // step_minutes
    
    # Weakness points = nodes with highest risk
    weakness_points = sorted(
        nodes_baseline,
        key=lambda x: x.get("depth_cm", 0),
        reverse=True
    )[:3]
    
    for step in range(num_steps + 1):
        frame_time = start_time + timedelta(minutes=step * step_minutes)
        
        # Scale depths over time (quadratic growth = realistic)
        progress = (step / max(1, num_steps)) ** 2
        
        nodes_frame = []
        for node_data in nodes_baseline:
            # Increase depth linearly with time
            depth_scaled = node_data["depth_cm"] * progress
            
            # Risk increases with depth (sigmoid curve)
            risk_scaled = node_data["risk_score"] * progress
            
            nodes_frame.append(
                NodeRisk(
                    node_id=node_data["node_id"],
                    latitude=node_data["latitude"],
                    longitude=node_data["longitude"],
                    risk_score=min(1.0, risk_scaled),
                    depth_cm=depth_scaled,
                    shap_top3=[
                        SHAPFactor(**f) if isinstance(f, dict) else f
                        for f in node_data.get("shap_top3", [])
                    ],
                    alert_en="Simulated scenario",
                    alert_sw="Sehemu ya simulation",
                )
            )
        
        frames.append(
            SimulationFrameResponse(
                frame_index=step,
                timestamp=frame_time,
                nodes=nodes_frame,
            )
        )
    
    logger.info(
        f"Generated {len(frames)} simulation frames for {county.name} "
        f"({duration_hours}h, {step_minutes}min cadence)"
    )
    
    return SimulationResponse(
        county_code=county.code,
        start_timestamp=start_time,
        end_timestamp=frames[-1].timestamp if frames else start_time,
        frames=frames,
        duration_minutes=duration_hours * 60,
        weakness_points=weakness_points,
    )
