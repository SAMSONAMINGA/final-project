"""
Extended Kalman Filter (EKF) for sensor fusion.
Combines three rainfall estimates: phone pressure, IMERG satellite, OpenWeather NWP.

Design decisions:
- State vector: [rainfall_intensity_mm_h, d_rainfall_dt]
- Three measurement sources with independent noise models
- Overeem et al. (2019) pressure-to-rainfall conversion
- Q (process noise), R (measurement noise) tunable per county
- Ref: Overeem et al. (2019) 'Phone barometers as a tool for meteorology'
"""

import numpy as np
from filterpy.kalman import ExtendedKalmanFilter as EKF
from typing import Tuple, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)


class RainfallEKF:
    """Extended Kalman Filter for rainfall estimation via sensor fusion."""
    
    def __init__(
        self,
        process_noise_q: float = 0.01,
        measurement_noise_r: float = 0.1,
        dt: float = 5.0,  # 5-minute timestep
    ):
        """
        Initialize rainfall EKF.
        
        Args:
            process_noise_q: Process noise (Q matrix) - how much we expect state to change
            measurement_noise_r: Measurement noise (R matrix) - sensor reliability
            dt: Timestep in minutes
        """
        self.dt = dt
        self.filter = EKF(dim_x=2, dim_z=3)  # 2D state, 3 measurements
        
        # State transition: [rainfall, d_rainfall_dt]
        # x[0]' = x[0] + x[1] * dt  (rainfall increases by rate)
        # x[1]' = x[1]             (rate stays constant)
        self.filter.F = np.array([
            [1.0, dt],
            [0.0, 1.0],
        ])
        
        # Measurement matrix: directly measure both rainfall and its rate
        self.filter.H = np.array([
            [1.0, 0.0],  # z1: pressure-derived rainfall
            [1.0, 0.0],  # z2: IMERG rainfall
            [1.0, 0.0],  # z3: OpenWeather rainfall
        ])
        
        # Process covariance (uncertainty in state evolution)
        self.filter.Q = np.eye(2) * process_noise_q
        
        # Measurement covariance (sensor noise)
        self.filter.R = np.eye(3) * measurement_noise_r
        
        # Initial state covariance (high uncertainty on startup)
        self.filter.P = np.eye(2) * 1.0
        
        # Initial state estimate
        self.filter.x = np.array([0.0, 0.0])
    
    def pressure_to_rainfall(self, pressure_prev_hpa: float, pressure_curr_hpa: float) -> float:
        """
        Convert pressure change to rainfall using Overeem et al. (2019) model.
        
        Simplified pressure-to-rainfall relationship:
        Rain(mm/h) = max(0, -dP/dt * sensitivity)
        
        where dP is pressure drop in hPa over time interval.
        Sensitivity ~0.1-0.3 mm/h per hPa/min based on Overeem et al.
        
        Args:
            pressure_prev_hpa: Previous pressure reading (hPa)
            pressure_curr_hpa: Current pressure reading (hPa)
        
        Returns:
            Estimated rainfall rate (mm/h)
        """
        # Pressure drop (positive = falling pressure = rain likely)
        delta_p = pressure_prev_hpa - pressure_curr_hpa
        
        # Sensitivity: 0.15 mm/h per hPa/min = 0.3 mm/h per 2 hPa drop in 5 min
        # Overeem calibration: ~0.1 for low-cost phone sensors
        sensitivity = 0.15
        
        # Time interval in minutes
        dt_min = self.dt
        
        # Pressure drop rate (hPa/min)
        delta_p_per_min = delta_p / dt_min
        
        # Rainfall estimate (clipped to non-negative)
        rainfall_mm_h = max(0.0, delta_p_per_min * sensitivity * 60)
        
        return rainfall_mm_h
    
    def update(
        self,
        pressure_prev_hpa: Optional[float] = None,
        pressure_curr_hpa: Optional[float] = None,
        imerg_rainfall_mm_h: Optional[float] = None,
        openweather_rainfall_mm_h: Optional[float] = None,
    ) -> Tuple[float, float]:
        """
        Update EKF with new measurements and return fused rainfall estimate.
        
        Args:
            pressure_prev_hpa: Previous barometer pressure
            pressure_curr_hpa: Current barometer pressure
            imerg_rainfall_mm_h: IMERG satellite estimate (mm/h)
            openweather_rainfall_mm_h: OpenWeather NWP estimate (mm/h)
        
        Returns:
            (estimated_rainfall_mm_h, rate_change_mm_h_per_5min)
        """
        # Predict step (using state transition model)
        self.filter.predict()
        
        # Build measurement vector (use None as 0 if source unavailable)
        measurements = []
        
        if pressure_prev_hpa is not None and pressure_curr_hpa is not None:
            z1 = self.pressure_to_rainfall(pressure_prev_hpa, pressure_curr_hpa)
        else:
            z1 = 0.0
        measurements.append(z1)
        
        if imerg_rainfall_mm_h is not None:
            measurements.append(imerg_rainfall_mm_h)
        else:
            measurements.append(0.0)
        
        if openweather_rainfall_mm_h is not None:
            measurements.append(openweather_rainfall_mm_h)
        else:
            measurements.append(0.0)
        
        z = np.array(measurements)
        
        # Update step (blend measurements with state estimate)
        self.filter.update(z)
        
        # Extract estimated rainfall intensity and rate of change
        rainfall_intensity = float(self.filter.x[0])
        rainfall_rate = float(self.filter.x[1])
        
        # Clamp to non-negative
        rainfall_intensity = max(0.0, rainfall_intensity)
        
        logger.debug(
            f"EKF update: z={z}, estimated_rainfall={rainfall_intensity:.2f} mm/h"
        )
        
        return rainfall_intensity, rainfall_rate
    
    def reset(self):
        """Reset filter state."""
        self.filter.x = np.array([0.0, 0.0])
        self.filter.P = np.eye(2) * 1.0
    
    def get_state_dict(self) -> Dict:
        """Export filter state (for caching/resumption)."""
        return {
            "x": self.filter.x.tolist(),
            "P": self.filter.P.tolist(),
            "Q": self.filter.Q.tolist(),
            "R": self.filter.R.tolist(),
        }
    
    def set_state_dict(self, state_dict: Dict):
        """Restore filter state."""
        self.filter.x = np.array(state_dict["x"])
        self.filter.P = np.array(state_dict["P"])
        self.filter.Q = np.array(state_dict["Q"])
        self.filter.R = np.array(state_dict["R"])


class CountyEKFManager:
    """Manager for EKF instances per county (47 total)."""
    
    def __init__(self):
        """Initialize EKF for all Kenya counties."""
        self.filters: Dict[str, RainfallEKF] = {}
        self._init_default_filters()
    
    def _init_default_filters(self):
        """Create EKF instances for all 47 counties with default parameters."""
        # Default noise parameters (can be tuned per county via admin endpoint)
        for county_code in [f"{i:02d}" for i in range(1, 48)]:
            self.filters[county_code] = RainfallEKF(
                process_noise_q=0.01,
                measurement_noise_r=0.1,
            )
    
    def get_or_create(self, county_code: str) -> RainfallEKF:
        """Get EKF for county, creating if necessary."""
        if county_code not in self.filters:
            self.filters[county_code] = RainfallEKF()
        return self.filters[county_code]
    
    def update_params(self, county_code: str, q: float, r: float):
        """Tune noise parameters for specific county."""
        ekf = self.get_or_create(county_code)
        ekf.filter.Q = np.eye(2) * q
        ekf.filter.R = np.eye(3) * r
        logger.info(f"Updated EKF params for {county_code}: Q={q}, R={r}")
    
    def load_from_json(self, json_path: str):
        """Load EKF parameters from JSON file."""
        try:
            with open(json_path, "r") as f:
                config = json.load(f)
            
            for county_code, params in config.items():
                if county_code in self.filters:
                    ekf = self.filters[county_code]
                    ekf.filter.Q = np.array(params["Q"])
                    ekf.filter.R = np.array(params["R"])
            
            logger.info(f"Loaded EKF config from {json_path}")
        except FileNotFoundError:
            logger.warning(f"EKF config file not found: {json_path}")
    
    def save_to_json(self, json_path: str):
        """Save all EKF parameters to JSON file."""
        config = {}
        for county_code, ekf in self.filters.items():
            config[county_code] = {
                "Q": ekf.filter.Q.tolist(),
                "R": ekf.filter.R.tolist(),
            }
        
        with open(json_path, "w") as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Saved EKF config to {json_path}")


# Global EKF manager instance
ekf_manager = CountyEKFManager()
