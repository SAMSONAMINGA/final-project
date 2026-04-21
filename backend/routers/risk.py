"""
Risk query endpoints.
GET /risk/{county_code} - Get heatmap for county (all nodes + risk scores + SHAP + alerts)
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from models.orm import RiskSnapshot, County
from schemas.api import RiskHeatmapResponse, NodeRisk, SHAPFactor
from utils.alerts import AlertGenerator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/{county_code}", response_model=RiskHeatmapResponse)
async def get_risk_heatmap(
    county_code: str,
    db: AsyncSession = Depends(get_session),
) -> RiskHeatmapResponse:
    """
    Get flood risk heatmap for county.
    
    Returns:
    - All drainage junctions with risk_score (0-1) and depth_cm
    - Top-3 SHAP factors per node (interpretability)
    - Natural language alerts (EN + SW)
    - Alert level classification (Low/Medium/High/Critical)
    
    Called by Next.js Mapbox frontend every 60 seconds.
    """
    # Find county
    county_result = await db.execute(
        select(County).where(County.code == county_code)
    )
    county = county_result.scalar_one_or_none()
    
    if not county:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"County {county_code} not found",
        )
    
    # Get latest risk snapshot
    result = await db.execute(
        select(RiskSnapshot)
        .where(RiskSnapshot.county_id == county.id)
        .order_by(RiskSnapshot.timestamp.desc())
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()
    
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No risk data available for {county.name}",
        )
    
    # Parse nodes
    nodes_data = snapshot.nodes_json or []
    alert_gen = AlertGenerator()
    
    nodes = []
    for node_data in nodes_data:
        risk_score = node_data["risk_score"]
        
        # Generate alerts in multiple languages
        alert_en = alert_gen.generate_sms(
            county.name,
            county_code,
            risk_score,
            rainfall_mm_h=5.0,  # Placeholder
            shap_factors=node_data.get("shap_top3"),
            language="en",
        )
        
        alert_sw = alert_gen.generate_sms(
            county.name,
            county_code,
            risk_score,
            rainfall_mm_h=5.0,
            shap_factors=node_data.get("shap_top3"),
            language="sw",
        )
        
        # Convert SHAP factors to schema
        shap_top3 = []
        for factor in node_data.get("shap_top3", []):
            shap_top3.append(
                SHAPFactor(
                    feature_name=factor.get("feature_name", "unknown"),
                    contribution=factor.get("contribution", 0.0),
                    value=factor.get("value"),
                )
            )
        
        nodes.append(
            NodeRisk(
                node_id=node_data["node_id"],
                latitude=node_data["latitude"],
                longitude=node_data["longitude"],
                risk_score=risk_score,
                depth_cm=node_data["depth_cm"],
                shap_top3=shap_top3,
                alert_en=alert_en,
                alert_sw=alert_sw,
            )
        )
    
    # Classify overall alert level
    alert_level = alert_gen.classify_risk(snapshot.max_risk_score)
    
    return RiskHeatmapResponse(
        county_code=county.code,
        county_name=county.name,
        timestamp=snapshot.timestamp,
        nodes=nodes,
        max_risk_score=snapshot.max_risk_score,
        max_depth_cm=snapshot.max_depth_cm,
        alert_level=alert_level,
    )
