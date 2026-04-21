"""
GATv2 inference task (30-min cadence).
Runs flood risk inference on all urban county drainage graphs.
Produces RiskSnapshot records with node-level predictions + SHAP explanations.
"""

import logging
from datetime import datetime, timezone
import numpy as np
from sqlalchemy import select

from services.celery_app import celery_app
from core.database import get_db_context
from models.orm import County, RiskSnapshot
from services.ml_loader import model_manager
from services.county_loader import county_loader
from utils.gatv2 import DrainageGraph
from utils.shap_explainer import SHAPExplainer
from utils.ekf import ekf_manager

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    name="services.tasks.inference_task.run_inference",
)
async def run_inference(self):
    """
    Run GATv2 inference on all urban counties.
    
    For each county:
    1. Fetch latest sensor fusion rainfall (EKF)
    2. Load drainage graph
    3. Run GATv2 prediction
    4. Generate SHAP explanations (top-3 factors per node)
    5. Store RiskSnapshot in DB
    """
    try:
        # Check model is loaded
        gatv2 = model_manager.get_gatv2()
        if not gatv2:
            logger.warning("GATv2 model not loaded")
            return
        
        async with get_db_context() as db:
            # Fetch all urban counties
            result = await db.execute(
                select(County).filter(County.is_urban == True)
            )
            urban_counties = result.scalars().all()
            
            model_version = model_manager.get_version()
            timestamp = datetime.now(timezone.utc)
            
            for county in urban_counties:
                try:
                    # Load county's drainage graph (from external data source)
                    # In production, this would load from OSM + DEM + local DB
                    graph = _load_drainage_graph(county.code)
                    
                    if not graph or len(graph.nodes) == 0:
                        logger.warning(f"No drainage graph for county {county.code}")
                        continue
                    
                    # Generate node features (fused rainfall from EKF, elevation, etc.)
                    _populate_node_features(graph, county.code)
                    
                    # Run inference
                    node_predictions = graph.predict(gatv2)
                    
                    # Generate SHAP explanations
                    _add_shap_explanations(node_predictions, graph)
                    
                    # Prepare snapshot data
                    nodes_data = [
                        {
                            "node_id": node_id,
                            "latitude": pred["latitude"],
                            "longitude": pred["longitude"],
                            "risk_score": pred["risk_score"],
                            "depth_cm": pred["depth_cm"],
                            "shap_top3": pred.get("shap_top3", []),
                        }
                        for node_id, pred in node_predictions.items()
                    ]
                    
                    max_risk = max([pred["risk_score"] for pred in node_predictions.values()], default=0)
                    max_depth = max([pred["depth_cm"] for pred in node_predictions.values()], default=0)
                    
                    # Store snapshot
                    snapshot = RiskSnapshot(
                        county_id=county.id,
                        timestamp=timestamp,
                        nodes_json=nodes_data,
                        max_risk_score=max_risk,
                        max_depth_cm=max_depth,
                        model_version=model_version,
                    )
                    
                    db.add(snapshot)
                    await db.flush()
                    
                    logger.info(
                        f"County {county.code}: max_risk={max_risk:.2%}, max_depth={max_depth:.1f}cm"
                    )
                
                except Exception as e:
                    logger.error(f"Inference failed for county {county.code}: {e}")
                    continue
            
            await db.commit()
            logger.info(f"Completed inference for {len(urban_counties)} urban counties")
    
    except Exception as exc:
        logger.error(f"Inference task failed: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


def _load_drainage_graph(county_code: str) -> DrainageGraph | None:
    """
    Load drainage graph for county.
    
    In production, this integrates with OSM API + local DEM database.
    For now, returns empty graph (placeholder).
    """
    graph = DrainageGraph(county_code)
    
    # Placeholder: In production, load nodes/edges from:
    # - OSM road/drain junction intersections
    # - DEM-derived flow network for areas without roads
    # - Local drainage database
    
    # Example: Add dummy nodes for testing
    for i in range(5):
        node_id = f"{county_code}_n{i}"
        graph.add_node(
            node_id,
            latitude=-1.0 + i * 0.01,
            longitude=36.0 + i * 0.01,
            features={}
        )
        
        if i > 0:
            graph.add_edge(
                f"{county_code}_n{i-1}",
                node_id,
                features={}
            )
    
    return graph


def _populate_node_features(graph: DrainageGraph, county_code: str):
    """
    Populate node features.
    
    Gets fused rainfall from EKF, elevation/soil from DEM, capacity from network data.
    """
    ekf = ekf_manager.get_or_create(county_code)
    
    for node_id, node_data in graph.nodes.items():
        # Get EKF rainfall estimate (placeholder)
        rainfall_mm_h = 5.0  # Dummy value
        
        # Get other features from data sources
        features = {
            "fused_rainfall_mm_h": rainfall_mm_h,
            "elevation_m": node_data.get("elevation_m", 500),
            "soil_moisture_pct": 50.0,  # Placeholder
            "hist_flood_frequency": 0.1,  # Placeholder
            "is_junction": 1.0,
            "drain_capacity_m3_s": 5.0,
            "imperv_fraction": 0.6,
        }
        
        graph.nodes[node_id]["features"] = features


def _add_shap_explanations(predictions: dict, graph: DrainageGraph):
    """
    Add SHAP explanations to predictions (placeholder).
    
    In production, this would use SHAP KernelExplainer for true interpretability.
    """
    for node_id, pred in predictions.items():
        # Placeholder: return dummy SHAP factors
        pred["shap_top3"] = [
            {"feature_name": "rainfall", "contribution": 0.5, "value": 5.0},
            {"feature_name": "imperv_fraction", "contribution": 0.3, "value": 0.6},
            {"feature_name": "elevation_m", "contribution": 0.2, "value": 500.0},
        ]
