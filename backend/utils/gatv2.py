"""
GATv2 (Graph Attention Network v2) for flood risk prediction.
Urban counties use full GATv2; rural counties use LSTM fallback.

Design decisions:
- PyTorch Geometric for training, ONNX Runtime for inference (no PyG dependency at runtime)
- GATv2Conv with 4 attention heads, 3 layers, 256 hidden units
- Node features (7-dim): [fused_rain, elevation, soil_moisture, hist_flood_freq, 
                          is_junction, drain_capacity, imperv_fraction]
- Edge features (4-dim): [slope_deg, surface_type_enc, blockage_score, pipe_diam_m]
- Output: [risk_score (sigmoid 0-1), depth_cm (ReLU)]
- Ref: Brody et al. (2021) GATv2 architecture improvements
"""

import numpy as np
import onnxruntime as rt
from typing import Tuple, List, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)


class GATv2Inference:
    """ONNX-based GATv2 inference for node-level flood risk."""
    
    # Node feature names and indices (must match training)
    NODE_FEATURES = [
        "fused_rainfall_mm_h",      # 0
        "elevation_m",              # 1
        "soil_moisture_pct",        # 2
        "hist_flood_frequency",     # 3 (0-1, fraction of previous floods)
        "is_junction",              # 4 (0 or 1)
        "drain_capacity_m3_s",      # 5
        "imperv_fraction",          # 6 (0-1, impervious cover)
    ]
    
    EDGE_FEATURES = [
        "slope_deg",                # 0
        "surface_type_enc",         # 1 (0=paved, 1=gravel, 2=dirt, 3=pipe)
        "blockage_score",           # 2 (0-1)
        "pipe_diameter_m",          # 3
    ]
    
    def __init__(self, model_path: str):
        """
        Load ONNX model.
        
        Args:
            model_path: Path to .onnx model file
        """
        try:
            # Use CPU by default; GPU if available
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            self.session = rt.InferenceSession(model_path, providers=providers)
            
            # Get input/output names
            self.input_names = [inp.name for inp in self.session.get_inputs()]
            self.output_names = [out.name for out in self.session.get_outputs()]
            
            logger.info(f"Loaded GATv2 model from {model_path}")
            logger.info(f"Inputs: {self.input_names}, Outputs: {self.output_names}")
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            raise
    
    def predict(
        self,
        node_features: np.ndarray,
        edge_index: np.ndarray,
        edge_features: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Run inference on drainage graph.
        
        Args:
            node_features: Shape (num_nodes, 7) - node feature matrix
            edge_index: Shape (2, num_edges) - connectivity [source, target] indices
            edge_features: Shape (num_edges, 4) - edge feature matrix
        
        Returns:
            (risk_scores, depths_cm)
            - risk_scores: (num_nodes,) - probability of flooding [0, 1]
            - depths_cm: (num_nodes,) - predicted water depth in cm (≥0)
        """
        # Prepare inputs for ONNX
        ort_inputs = {
            "node_features": node_features.astype(np.float32),
            "edge_index": edge_index.astype(np.int64),
            "edge_features": edge_features.astype(np.float32),
        }
        
        # Run inference
        ort_outs = self.session.run(self.output_names, ort_inputs)
        
        # Extract outputs
        risk_scores = ort_outs[0].flatten()  # Sigmoid already applied in model
        depths_cm = ort_outs[1].flatten()    # ReLU already applied
        
        return risk_scores, depths_cm
    
    @staticmethod
    def validate_node_features(features: Dict[str, float]) -> bool:
        """Validate node feature dict has all required keys."""
        return all(key in features for key in GATv2Inference.NODE_FEATURES)
    
    @staticmethod
    def validate_edge_features(features: Dict[str, float]) -> bool:
        """Validate edge feature dict has all required keys."""
        return all(key in features for key in GATv2Inference.EDGE_FEATURES)


class DrainageGraph:
    """
    Directed drainage graph for a county.
    Nodes = road/drain junctions from OSM + DEM-derived.
    Edges = flow direction (uphill to downhill).
    """
    
    def __init__(self, county_code: str):
        """
        Initialize graph for county.
        
        Args:
            county_code: "01" to "47"
        """
        self.county_code = county_code
        self.nodes: Dict[str, Dict] = {}  # node_id -> {lat, lon, features}
        self.edges: List[Tuple[str, str, Dict]] = []  # [(src, dst, features), ...]
    
    def add_node(
        self,
        node_id: str,
        latitude: float,
        longitude: float,
        features: Dict[str, float],
    ):
        """Add node to graph."""
        self.nodes[node_id] = {
            "latitude": latitude,
            "longitude": longitude,
            "features": features,
        }
    
    def add_edge(
        self,
        src_node_id: str,
        dst_node_id: str,
        features: Dict[str, float],
    ):
        """Add directed edge (src -> dst, following flow direction)."""
        self.edges.append((src_node_id, dst_node_id, features))
    
    def to_tensors(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
        """
        Convert graph to tensor format for ONNX inference.
        
        Returns:
            (node_features, edge_index, edge_features, node_ids)
        """
        # Sort nodes by ID for consistent ordering
        sorted_node_ids = sorted(self.nodes.keys())
        node_id_to_idx = {nid: idx for idx, nid in enumerate(sorted_node_ids)}
        
        # Build node feature matrix
        num_nodes = len(sorted_node_ids)
        node_features = np.zeros((num_nodes, len(GATv2Inference.NODE_FEATURES)), dtype=np.float32)
        
        for idx, node_id in enumerate(sorted_node_ids):
            features = self.nodes[node_id]["features"]
            for feat_idx, feat_name in enumerate(GATv2Inference.NODE_FEATURES):
                node_features[idx, feat_idx] = features.get(feat_name, 0.0)
        
        # Build edge index and edge features
        num_edges = len(self.edges)
        edge_index = np.zeros((2, num_edges), dtype=np.int64)
        edge_features = np.zeros((num_edges, len(GATv2Inference.EDGE_FEATURES)), dtype=np.float32)
        
        for edge_idx, (src_id, dst_id, features) in enumerate(self.edges):
            src_idx = node_id_to_idx.get(src_id, 0)
            dst_idx = node_id_to_idx.get(dst_id, 0)
            
            edge_index[0, edge_idx] = src_idx
            edge_index[1, edge_idx] = dst_idx
            
            for feat_idx, feat_name in enumerate(GATv2Inference.EDGE_FEATURES):
                edge_features[edge_idx, feat_idx] = features.get(feat_name, 0.0)
        
        return node_features, edge_index, edge_features, sorted_node_ids
    
    def predict(self, model: GATv2Inference) -> Dict[str, Dict]:
        """
        Run GATv2 inference on this graph.
        
        Returns:
            Dict mapping node_id -> {risk_score, depth_cm, latitude, longitude}
        """
        node_features, edge_index, edge_features, node_ids = self.to_tensors()
        
        risk_scores, depths_cm = model.predict(node_features, edge_index, edge_features)
        
        results = {}
        for idx, node_id in enumerate(node_ids):
            node_data = self.nodes[node_id]
            results[node_id] = {
                "risk_score": float(risk_scores[idx]),
                "depth_cm": float(depths_cm[idx]),
                "latitude": node_data["latitude"],
                "longitude": node_data["longitude"],
            }
        
        return results


class LSTMFallback:
    """LSTM fallback for rural counties."""
    
    def __init__(self):
        """Initialize LSTM fallback model."""
        # Placeholder: in production, load LSTM ONNX model
        pass
    
    def predict(self, rainfall_history: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        LSTM prediction for counties without drainage graph.
        
        Args:
            rainfall_history: Shape (num_timesteps, num_counties)
        
        Returns:
            (risk_scores, depths_cm) for representative nodes
        """
        # Placeholder
        return np.zeros(10), np.zeros(10)


def get_model_for_county(county_code: str, is_urban: bool, model_path: str) -> GATv2Inference | LSTMFallback:
    """
    Get appropriate model for county type.
    
    Args:
        county_code: "01" to "47"
        is_urban: True for Nairobi/Mombasa/etc
        model_path: Path to ONNX model
    
    Returns:
        Model instance (GATv2 or LSTM fallback)
    """
    if is_urban:
        return GATv2Inference(model_path)
    else:
        return LSTMFallback()
