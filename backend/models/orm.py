"""
SQLAlchemy 2.0 ORM models for all database tables.
Uses GeoAlchemy2 for PostGIS spatial columns.

Design decisions:
- All tables with timestamps (created_at, updated_at) for audit trail
- Immutable tables for audit_logs and alert_logs (enforce at DB level)
- Composite indexes on (county_code, time) for efficient time-series queries
- Spatial indexes (GiST) on all GEOMETRY/POINT columns
- Foreign keys with ON DELETE CASCADE for referential integrity
- Use JSONB for flexible IMERG grids and risk snapshots
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, JSONB, Index,
    ForeignKey, Enum as SQLEnum, func, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry, Geography
from datetime import datetime, timezone
from enum import Enum
import uuid

from core.database import Base


# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, Enum):
    """User roles for RBAC."""
    USER = "user"
    ADMIN = "admin"


class AlertChannel(str, Enum):
    """Alert delivery channels."""
    SMS = "sms"
    USSD = "ussd"
    PUSH = "push"


# ============================================================================
# TABLES
# ============================================================================

class User(Base):
    """Users table for authentication and RBAC."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    __table_args__ = (
        Index("idx_users_username", "username"),
        Index("idx_users_email", "email"),
        Index("idx_users_is_active", "is_active"),
    )


class RefreshToken(Base):
    """Refresh tokens table for token revocation."""
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_jti = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")


class County(Base):
    """Kenya counties (ADM1) with PostGIS MULTIPOLYGON geometry."""
    __tablename__ = "counties"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(2), unique=True, nullable=False, index=True)  # "01" to "47"
    name = Column(String(100), unique=True, nullable=False, index=True)
    geometry = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)
    centroid = Column(Geometry("POINT", srid=4326), nullable=False)
    is_urban = Column(Boolean, default=False, nullable=False)  # Use GATv2 if True, LSTM if False
    population = Column(Integer, nullable=True)
    area_km2 = Column(Float, nullable=True)
    avg_elevation_m = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    risk_snapshots = relationship("RiskSnapshot", back_populates="county")
    barometer_readings = relationship("BarometerReading", back_populates="county")
    openweather_snapshots = relationship("OpenWeatherSnapshot", back_populates="county")
    
    __table_args__ = (
        Index("idx_counties_code", "code"),
        Index("idx_counties_name", "name"),
        Index("idx_counties_is_urban", "is_urban"),
        Index("idx_counties_geometry", "geometry", postgresql_using="gist"),
    )


class BarometerReading(Base):
    """
    Anonymised barometer readings from Android volunteer devices.
    Hashed device_id only (no PII); pressure readings + GPS point.
    """
    __tablename__ = "barometer_readings"
    
    id = Column(Integer, primary_key=True, index=True)
    county_id = Column(Integer, ForeignKey("counties.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    pressure_hpa = Column(Float, nullable=False)
    altitude_m = Column(Float, nullable=True)
    temperature_c = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    county = relationship("County", back_populates="barometer_readings")
    
    __table_args__ = (
        Index("idx_barometer_device_id_hash", "device_id_hash"),
        Index("idx_barometer_county_id_time", "county_id", "timestamp"),
        Index("idx_barometer_location", "location", postgresql_using="gist"),
        CheckConstraint("pressure_hpa > 0", name="check_pressure_positive"),
    )


class IMERGSnapshot(Base):
    """
    NASA GPM-IMERG Early Run snapshots (30-min cadence).
    Stores JSONB grid of precipitation mm/h across Kenya bbox.
    """
    __tablename__ = "imerg_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, unique=True, index=True)
    grid_json = Column(JSONB, nullable=False)  # {"west": 33.9, "south": -4.7, "grid": [...]}
    source_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    
    __table_args__ = (
        Index("idx_imerg_timestamp", "timestamp"),
    )


class OpenWeatherSnapshot(Base):
    """
    OpenWeather One Call 3.0 snapshots per county centroid (30-min cadence).
    Includes current conditions, 1h forecast, 48h forecast.
    """
    __tablename__ = "openweather_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    county_id = Column(Integer, ForeignKey("counties.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    data_json = Column(JSONB, nullable=False)  # Full OpenWeather JSON response
    current_precip_mm_h = Column(Float, nullable=True)
    forecast_precip_mm_h = Column(Float, nullable=True)  # Next 1-3 hours averaged
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    county = relationship("County", back_populates="openweather_snapshots")
    
    __table_args__ = (
        Index("idx_openweather_county_id_time", "county_id", "timestamp"),
    )


class RiskSnapshot(Base):
    """
    GATv2 inference output snapshot per county.
    Immutable record of node-level risk scores and depths.
    """
    __tablename__ = "risk_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    county_id = Column(Integer, ForeignKey("counties.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    nodes_json = Column(JSONB, nullable=False)  # [{node_id, risk_score, depth_cm, shap_top3, ...}]
    max_risk_score = Column(Float, nullable=False)  # Summary statistic
    max_depth_cm = Column(Float, nullable=False)
    model_version = Column(String(50), nullable=False)  # e.g. "v1.2.0"
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    county = relationship("County", back_populates="risk_snapshots")
    
    __table_args__ = (
        Index("idx_risk_county_id_time", "county_id", "timestamp"),
        CheckConstraint("max_risk_score >= 0 AND max_risk_score <= 1", name="check_risk_score"),
    )


class AlertLog(Base):
    """
    Immutable log of all SMS/USSD alerts dispatched.
    No updates/deletes allowed (enforce at application layer).
    """
    __tablename__ = "alert_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    county_code = Column(String(2), nullable=False, index=True)
    channel = Column(SQLEnum(AlertChannel), nullable=False, index=True)
    phone_number_hash = Column(String(64), nullable=False, index=True)  # SHA-256
    message_body = Column(Text, nullable=False)
    shap_factors = Column(JSONB, nullable=True)  # Top-3 SHAP factors
    alert_level = Column(String(20), nullable=False)  # "Low", "Medium", "High", "Critical"
    sent_at = Column(DateTime(timezone=True), nullable=False, index=True)
    delivery_status = Column(String(50), nullable=True)  # "pending", "delivered", "failed"
    delivery_timestamp = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    
    __table_args__ = (
        Index("idx_alert_county_code", "county_code"),
        Index("idx_alert_sent_at", "sent_at"),
        Index("idx_alert_phone_number_hash", "phone_number_hash"),
    )


class AuditLog(Base):
    """
    Immutable audit trail for all admin actions.
    No updates/deletes allowed.
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # "retrain_model", "update_ekf", etc.
    resource_type = Column(String(100), nullable=False)  # "model", "ekf_params", "volunteer_device"
    resource_id = Column(String(255), nullable=True)
    changes = Column(JSONB, nullable=True)  # {"old": {...}, "new": {...}}
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(512), nullable=True)
    status = Column(String(20), nullable=False)  # "success" or "failure"
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    __table_args__ = (
        Index("idx_audit_user_id", "user_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_created_at", "created_at"),
    )
