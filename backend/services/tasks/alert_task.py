"""
Alert dispatch task.
Generates and sends SMS/USSD alerts based on risk snapshots.
Triggered manually via POST /alerts/send endpoint.
"""

import logging
from datetime import datetime, timezone
from sqlalchemy import select

from services.celery_app import celery_app
from core.database import get_db_context
from models.orm import AlertLog, County
from utils.alerts import AlertGenerator, AfricasTalkingDispatcher, hash_phone_number
from utils.shap_explainer import SHAPExplainer
from core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=2,
    name="services.tasks.alert_task.dispatch_alert",
)
async def dispatch_alert(
    self,
    county_code: str,
    phone_number: str,
    language: str = "en",
    include_shap: bool = True,
):
    """
    Generate and dispatch alert for county.
    
    Args:
        county_code: "01" to "47"
        phone_number: Recipient phone number
        language: "en", "sw", or "sh"
        include_shap: Include SHAP explanations in message
    """
    try:
        async with get_db_context() as db:
            # Get latest risk snapshot for county
            from models.orm import RiskSnapshot
            
            result = await db.execute(
                select(County).filter(County.code == county_code)
            )
            county = result.scalar_one_or_none()
            
            if not county:
                logger.error(f"County {county_code} not found")
                return
            
            # Get latest risk snapshot
            risk_result = await db.execute(
                select(RiskSnapshot)
                .filter(RiskSnapshot.county_id == county.id)
                .order_by(RiskSnapshot.timestamp.desc())
                .limit(1)
            )
            risk_snapshot = risk_result.scalar_one_or_none()
            
            if not risk_snapshot:
                logger.warning(f"No risk snapshot for county {county_code}")
                return
            
            # Extract max risk and derive rainfall estimate
            max_risk = risk_snapshot.max_risk_score
            rainfall_mm_h = max_risk * 50  # Simple scaling
            
            # Get SHAP factors if available
            shap_factors = None
            if include_shap and risk_snapshot.nodes_json:
                nodes = risk_snapshot.nodes_json
                if nodes and len(nodes) > 0:
                    shap_factors = nodes[0].get("shap_top3", None)
            
            # Generate alert message
            generator = AlertGenerator()
            
            # For now, send SMS (SMS is more reliable than USSD)
            message = generator.generate_sms(
                county_name=county.name,
                county_code=county.code,
                risk_score=max_risk,
                rainfall_mm_h=rainfall_mm_h,
                shap_factors=shap_factors,
                language=language,
            )
            
            # Dispatch via Africa's Talking
            dispatcher = AfricasTalkingDispatcher(
                settings.africas_talking_api_key,
                settings.africas_talking_username,
            )
            
            msg_id = await dispatcher.send_sms(phone_number, message)
            
            # Log alert
            alert_log = AlertLog(
                county_code=county.code,
                channel="sms",
                phone_number_hash=hash_phone_number(phone_number),
                message_body=message,
                shap_factors=shap_factors,
                alert_level=generator.classify_risk(max_risk),
                sent_at=datetime.now(timezone.utc),
                delivery_status="sent" if msg_id else "failed",
            )
            
            db.add(alert_log)
            await db.commit()
            
            logger.info(f"Alert dispatched to {phone_number} for {county_code}")
            
            await dispatcher.close()
    
    except Exception as exc:
        logger.error(f"Alert dispatch failed: {exc}")
        raise self.retry(exc=exc, countdown=60)
