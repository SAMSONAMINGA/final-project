"""
SHAP (SHapley Additive exPlanations) explainer for GATv2 predictions.
Generates per-node explanations: top-3 contributing features for each risk score.

Design decisions:
- KernelExplainer for post-hoc explanations (model-agnostic)
- Explain which node features drive risk prediction
- Cache explanations to avoid recomputation
- Top-3 factors returned for alert generation
- Ref: Lundberg & Lee (2017) SHAP unified framework
"""

import numpy as np
import shap
from typing import Dict, List, Optional, Callable
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SHAPExplainer:
    """SHAP KernelExplainer for GATv2 output interpretability."""
    
    # Node feature names
    NODE_FEATURES = [
        "fused_rainfall_mm_h",
        "elevation_m",
        "soil_moisture_pct",
        "hist_flood_frequency",
        "is_junction",
        "drain_capacity_m3_s",
        "imperv_fraction",
    ]
    
    def __init__(
        self,
        predict_fn: Callable,
        background_data: np.ndarray,
        sample_size: int = 100,
    ):
        """
        Initialize SHAP explainer.
        
        Args:
            predict_fn: Function that takes node_features (N, 7) and returns risk scores (N,)
            background_data: Background dataset for SHAP (typically random samples)
            sample_size: Number of samples for KernelExplainer
        """
        self.predict_fn = predict_fn
        self.sample_size = sample_size
        self.explainer = None
        
        # Initialize KernelExplainer with background data
        try:
            # Use small background for speed
            background_subset = background_data[:min(50, len(background_data))]
            
            self.explainer = shap.KernelExplainer(
                model=self._wrapper_fn,
                data=shap.sample(background_subset, min(sample_size, len(background_subset))),
            )
            
            logger.info(f"SHAP explainer initialized with sample size {self.sample_size}")
        except Exception as e:
            logger.error(f"Failed to initialize SHAP explainer: {e}")
    
    def _wrapper_fn(self, X: np.ndarray) -> np.ndarray:
        """Wrapper for SHAP (handles batch predictions)."""
        try:
            return self.predict_fn(X)
        except Exception as e:
            logger.error(f"Prediction error in SHAP wrapper: {e}")
            return np.zeros(len(X))
    
    def explain_node(self, node_features: np.ndarray, top_k: int = 3) -> List[Dict]:
        """
        Explain prediction for single node.
        
        Args:
            node_features: Feature vector (7,) for one junction
            top_k: Number of top factors to return
        
        Returns:
            List of dicts: [{"feature": name, "contribution": float, "value": float}, ...]
        """
        if self.explainer is None:
            logger.warning("SHAP explainer not initialized")
            return []
        
        try:
            # Get SHAP values
            shap_values = self.explainer.shap_values(
                np.array([node_features]),
                check_additivity=False,
            )
            
            # shap_values shape: (1, num_features) or (num_classes, 1, num_features)
            if isinstance(shap_values, list):
                # Multi-class output
                shap_vals = shap_values[0][0]
            else:
                shap_vals = shap_values[0]
            
            # Get absolute contributions
            contributions = np.abs(shap_vals)
            
            # Get top-k indices
            top_indices = np.argsort(contributions)[-top_k:][::-1]
            
            # Build explanation dicts
            explanations = []
            for idx in top_indices:
                explanations.append({
                    "feature_name": self.NODE_FEATURES[idx] if idx < len(self.NODE_FEATURES) else "unknown",
                    "contribution": float(contributions[idx]),
                    "value": float(node_features[idx]),
                    "direction": "increases risk" if shap_vals[idx] > 0 else "decreases risk",
                })
            
            return explanations
        
        except Exception as e:
            logger.error(f"SHAP explanation error: {e}")
            return []
    
    def explain_batch(
        self,
        node_features: np.ndarray,
        top_k: int = 3,
    ) -> List[List[Dict]]:
        """
        Explain predictions for multiple nodes.
        
        Args:
            node_features: (N, 7) feature matrix
            top_k: Top factors per node
        
        Returns:
            List of explanation lists
        """
        if self.explainer is None:
            return [[] for _ in range(len(node_features))]
        
        try:
            shap_values = self.explainer.shap_values(
                node_features,
                check_additivity=False,
            )
            
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            
            explanations = []
            for i, shap_vals in enumerate(shap_values):
                contributions = np.abs(shap_vals)
                top_indices = np.argsort(contributions)[-top_k:][::-1]
                
                node_exp = []
                for idx in top_indices:
                    node_exp.append({
                        "feature_name": self.NODE_FEATURES[idx] if idx < len(self.NODE_FEATURES) else "unknown",
                        "contribution": float(contributions[idx]),
                        "value": float(node_features[i, idx]),
                        "direction": "increases risk" if shap_vals[idx] > 0 else "decreases risk",
                    })
                
                explanations.append(node_exp)
            
            return explanations
        
        except Exception as e:
            logger.error(f"Batch SHAP error: {e}")
            return [[] for _ in range(len(node_features))]


class SHAPCache:
    """Cache for SHAP explanations (expensive to compute)."""
    
    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize cache.
        
        Args:
            ttl_seconds: Time-to-live for cached explanations
        """
        self.cache: Dict[str, tuple[datetime, List[Dict]]] = {}
        self.ttl = timedelta(seconds=ttl_seconds)
    
    def _key_for_features(self, features: np.ndarray) -> str:
        """Generate cache key from feature vector."""
        # Use hash of rounded features
        feature_str = "_".join([f"{f:.2f}" for f in features])
        return feature_str
    
    def get(self, features: np.ndarray) -> Optional[List[Dict]]:
        """Get cached explanation if valid."""
        key = self._key_for_features(features)
        
        if key in self.cache:
            timestamp, explanation = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                logger.debug(f"Cache hit for {key}")
                return explanation
            else:
                del self.cache[key]
        
        return None
    
    def set(self, features: np.ndarray, explanation: List[Dict]):
        """Cache explanation."""
        key = self._key_for_features(features)
        self.cache[key] = (datetime.now(), explanation)
    
    def clear(self):
        """Clear all cache."""
        self.cache.clear()
        logger.info("SHAP cache cleared")
