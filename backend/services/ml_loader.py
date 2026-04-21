"""
ML model loader and manager.
Handles ONNX model loading, versioning, and fallback strategies.

Design decisions:
- Load ONNX model once at startup (immutable during runtime)
- Keep both GATv2 (urban) and LSTM (rural) models loaded
- Monitor model file timestamp for reload detection
- Pre-allocate inference sessions for speed
"""

import os
from pathlib import Path
import logging
from datetime import datetime
import onnxruntime as rt

from core.config import settings
from utils.gatv2 import GATv2Inference, LSTMFallback

logger = logging.getLogger(__name__)


class MLModelManager:
    """Manages ML model lifecycle (loading, caching, versioning)."""
    
    def __init__(self):
        """Initialize model manager."""
        self.gatv2_model: GATv2Inference | None = None
        self.lstm_model: LSTMFallback | None = None
        self.model_path = Path(settings.model_path)
        self.last_load_time: datetime | None = None
        self.model_version: str = "unknown"
    
    def load_models(self):
        """Load all models from disk."""
        try:
            # Load GATv2 ONNX model
            if self.model_path.exists():
                self.gatv2_model = GATv2Inference(str(self.model_path))
                self.last_load_time = datetime.now()
                
                # Extract version from filename (e.g., gatv2_geoflood_v1.2.0.onnx)
                filename = self.model_path.stem
                if "_v" in filename:
                    self.model_version = "v" + filename.split("_v")[-1]
                else:
                    self.model_version = "unknown"
                
                logger.info(f"Loaded GATv2 model (version: {self.model_version})")
            else:
                logger.warning(f"GATv2 model not found at {self.model_path}")
                self.gatv2_model = None
            
            # Initialize LSTM fallback
            self.lstm_model = LSTMFallback()
            logger.info("Initialized LSTM fallback model")
        
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            raise
    
    def get_gatv2(self) -> GATv2Inference | None:
        """Get loaded GATv2 model."""
        return self.gatv2_model
    
    def get_lstm(self) -> LSTMFallback | None:
        """Get LSTM fallback model."""
        return self.lstm_model
    
    def check_reload_needed(self) -> bool:
        """Check if model file has changed on disk."""
        if not self.model_path.exists():
            return False
        
        file_mtime = datetime.fromtimestamp(self.model_path.stat().st_mtime)
        
        if self.last_load_time is None:
            return True
        
        return file_mtime > self.last_load_time
    
    def reload_if_needed(self):
        """Reload models if file has changed."""
        if self.check_reload_needed():
            logger.info("Model file changed, reloading...")
            self.load_models()
    
    def get_version(self) -> str:
        """Get current model version."""
        return self.model_version


# Global model manager instance
model_manager = MLModelManager()
