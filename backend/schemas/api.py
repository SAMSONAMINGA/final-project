"""
Pydantic v2 schemas for API request/response validation.

Design decisions:
- Strict input validation using field_validator
- Kenya bbox bounds checked on all GPS coordinates
- Phone number hashing before storage (no PII in logs)
- Output schemas exclude sensitive fields
- Separate read/write schemas for ORM compatibility
"""

from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class UserRoleEnum(str, Enum):
    """User role options."""
    USER = "user"
    ADMIN = "admin"


class AlertChannelEnum(str, Enum):
    """Alert delivery channels."""
    SMS = "sms"
    USSD = "ussd"
    PUSH = "push"


# ============================================================================
# AUTH SCHEMAS
# ============================================================================

class LoginRequest(BaseModel):
    """Login request with username and password."""
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=255)


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""
    refresh_token: str


class CreateUserRequest(BaseModel):
    """Admin request to create new user."""
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)
    role: UserRoleEnum = UserRoleEnum.USER


class UserResponse(BaseModel):
    """User data (no password)."""
    id: int
    username: str
    email: str
    role: UserRoleEnum
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ============================================================================
# BAROMETER SCHEMAS
# ============================================================================

class BarometerReading(BaseModel):
    """Single barometer reading from Android volunteer device."""
    device_id: str = Field(..., description="Unique device identifier (will be hashed)")
    latitude: float = Field(..., ge=-4.7, le=5.0, description="Kenya bbox")
    longitude: float = Field(..., ge=33.9, le=41.9, description="Kenya bbox")
    pressure_hpa: float = Field(..., gt=0, le=1100, description="Valid atmospheric pressure")
    altitude_m: Optional[float] = Field(None, ge=-100, le=5000)
    temperature_c: Optional[float] = Field(None, ge=-50, le=60)
    humidity_pct: Optional[float] = Field(None, ge=0, le=100)
    timestamp: datetime
    
    @field_validator("latitude", "longitude")
    @classmethod
    def validate_bounds(cls, v, info):
        """Ensure coordinates within Kenya bbox."""
        if info.field_name == "latitude" and not (-4.7 <= v <= 5.0):
            raise ValueError("Latitude outside Kenya bounds (-4.7 to 5.0)")
        if info.field_name == "longitude" and not (33.9 <= v <= 41.9):
            raise ValueError("Longitude outside Kenya bounds (33.9 to 41.9)")
        return v


class BarometerBatchRequest(BaseModel):
    """Batch ingest up to 12 barometer readings."""
    readings: List[BarometerReading] = Field(..., max_length=12, min_length=1)


class BarometerReadingResponse(BaseModel):
    """Response after ingesting barometer reading."""
    id: int
    timestamp: datetime
    created_at: datetime


# ============================================================================
# RISK SCHEMAS
# ============================================================================

class SHAPFactor(BaseModel):
    """Single SHAP explanation factor."""
    feature_name: str
    contribution: float
    value: Any


class NodeRisk(BaseModel):
    """Risk data for single graph node."""
    node_id: str
    latitude: float
    longitude: float
    risk_score: float = Field(..., ge=0, le=1, description="Probability of flooding")
    depth_cm: float = Field(..., ge=0, description="Predicted water depth")
    shap_top3: List[SHAPFactor]
    alert_en: str  # English message
    alert_sw: str  # Swahili message


class RiskHeatmapResponse(BaseModel):
    """Full risk heatmap for a county."""
    county_code: str
    county_name: str
    timestamp: datetime
    nodes: List[NodeRisk]
    max_risk_score: float
    max_depth_cm: float
    alert_level: str  # "Low", "Medium", "High", "Critical"


# ============================================================================
# SIMULATION SCHEMAS
# ============================================================================

class SimulationFrameResponse(BaseModel):
    """Single time-stepped frame for Cesium 3D animation."""
    frame_index: int
    timestamp: datetime
    nodes: List[NodeRisk]


class SimulationResponse(BaseModel):
    """Full simulation output for 3D animation."""
    county_code: str
    start_timestamp: datetime
    end_timestamp: datetime
    frames: List[SimulationFrameResponse]
    duration_minutes: int
    weakness_points: List[Dict[str, Any]]  # High-risk junctions


# ============================================================================
# ALERT SCHEMAS
# ============================================================================

class SendAlertRequest(BaseModel):
    """Request to generate and dispatch alert."""
    county_code: str = Field(..., min_length=2, max_length=2)
    phone_number: str = Field(..., description="Will be hashed before storage")
    language: str = Field(default="en", pattern="^(en|sw|sh)$")  # English/Swahili/Sheng
    include_shap: bool = Field(default=True, description="Include SHAP factors in message")


class AlertDispatchResponse(BaseModel):
    """Confirmation that alert was dispatched."""
    alert_id: int
    county_code: str
    channel: AlertChannelEnum
    sent_at: datetime
    delivery_status: str


class AfricasTalkingWebhookPayload(BaseModel):
    """Webhook payload from Africa's Talking delivery reports."""
    id: str
    phoneNumber: str
    status: str  # "Success", "Failed", "Queued"
    networkCode: str
    retryCount: Optional[int] = None


# ============================================================================
# ADMIN SCHEMAS
# ============================================================================

class EKFTuneRequest(BaseModel):
    """Request to update EKF noise parameters."""
    county_code: str = Field(..., min_length=2, max_length=2)
    process_noise: float = Field(..., gt=0, description="Q matrix value")
    measurement_noise: float = Field(..., gt=0, description="R matrix value")
    reason: Optional[str] = None


class VolunteerDeviceRequest(BaseModel):
    """Request to register volunteer device."""
    device_id: str = Field(..., min_length=1, max_length=255)
    phone_number: str = Field(..., description="Will be hashed")
    county_code: str = Field(..., min_length=2, max_length=2)
    language: str = Field(default="en", pattern="^(en|sw|sh)$")


class VolunteerDeviceResponse(BaseModel):
    """Volunteer device registration confirmation."""
    device_id_hash: str
    phone_number_hash: str
    county_code: str
    registered_at: datetime


class RetrainingJobResponse(BaseModel):
    """Response when triggering model retraining."""
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    started_at: datetime


class AuditLogEntry(BaseModel):
    """Single audit log entry."""
    id: int
    user_id: Optional[int]
    action: str
    resource_type: str
    resource_id: Optional[str]
    changes: Optional[Dict[str, Any]]
    status: str
    error_message: Optional[str]
    created_at: datetime


class AuditLogsResponse(BaseModel):
    """Paginated audit logs."""
    total: int
    page: int
    page_size: int
    entries: List[AuditLogEntry]


# ============================================================================
# HEALTH SCHEMAS
# ============================================================================

class HealthCheckResponse(BaseModel):
    """System health status."""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    components: Dict[str, str]  # {"database": "ok", "redis": "ok", "ml_model": "ok"}
