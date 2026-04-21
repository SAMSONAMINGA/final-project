"""
Initial Alembic migration: Create all tables with spatial indexes.

Generated from ORM models:
- users, refresh_tokens
- counties (PostGIS MULTIPOLYGON)
- barometer_readings (PostGIS POINT)
- imerg_snapshots, openweather_snapshots
- risk_snapshots
- alert_logs, audit_logs
"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables."""
    
    # Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("user", "admin", name="userrole"), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_users_username", "users", ["username"])
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_is_active", "users", ["is_active"])
    
    # Create refresh_tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_jti", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_refresh_user_id", "refresh_tokens", ["user_id"])
    op.create_index("idx_refresh_expires_at", "refresh_tokens", ["expires_at"])
    
    # Create counties table
    op.create_table(
        "counties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(2), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("geometry", Geometry("MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("centroid", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("is_urban", sa.Boolean(), default=False, nullable=False),
        sa.Column("population", sa.Integer()),
        sa.Column("area_km2", sa.Float()),
        sa.Column("avg_elevation_m", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_counties_code", "counties", ["code"])
    op.create_index("idx_counties_name", "counties", ["name"])
    op.create_index("idx_counties_is_urban", "counties", ["is_urban"])
    op.create_index("idx_counties_geometry", "counties", ["geometry"], postgresql_using="gist")
    
    # Create barometer_readings table
    op.create_table(
        "barometer_readings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("county_id", sa.Integer(), nullable=False),
        sa.Column("device_id_hash", sa.String(64), nullable=False),
        sa.Column("location", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("pressure_hpa", sa.Float(), nullable=False),
        sa.Column("altitude_m", sa.Float()),
        sa.Column("temperature_c", sa.Float()),
        sa.Column("humidity_pct", sa.Float()),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["county_id"], ["counties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("pressure_hpa > 0", name="check_pressure_positive"),
    )
    op.create_index("idx_barometer_device_id", "barometer_readings", ["device_id_hash"])
    op.create_index("idx_barometer_county_time", "barometer_readings", ["county_id", "timestamp"])
    op.create_index("idx_barometer_location", "barometer_readings", ["location"], postgresql_using="gist")
    
    # Create imerg_snapshots table
    op.create_table(
        "imerg_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, unique=True),
        sa.Column("grid_json", sa.JSON(), nullable=False),
        sa.Column("source_url", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_imerg_timestamp", "imerg_snapshots", ["timestamp"])
    
    # Create openweather_snapshots table
    op.create_table(
        "openweather_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("county_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_json", sa.JSON(), nullable=False),
        sa.Column("current_precip_mm_h", sa.Float()),
        sa.Column("forecast_precip_mm_h", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["county_id"], ["counties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_openweather_county_time", "openweather_snapshots", ["county_id", "timestamp"])
    
    # Create risk_snapshots table
    op.create_table(
        "risk_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("county_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nodes_json", sa.JSON(), nullable=False),
        sa.Column("max_risk_score", sa.Float(), nullable=False),
        sa.Column("max_depth_cm", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["county_id"], ["counties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("max_risk_score >= 0 AND max_risk_score <= 1", name="check_risk_score"),
    )
    op.create_index("idx_risk_county_time", "risk_snapshots", ["county_id", "timestamp"])
    
    # Create alert_logs table
    op.create_table(
        "alert_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("county_code", sa.String(2), nullable=False),
        sa.Column("channel", sa.Enum("sms", "ussd", "push", name="alertchannel"), nullable=False),
        sa.Column("phone_number_hash", sa.String(64), nullable=False),
        sa.Column("message_body", sa.Text(), nullable=False),
        sa.Column("shap_factors", sa.JSON()),
        sa.Column("alert_level", sa.String(20), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivery_status", sa.String(50)),
        sa.Column("delivery_timestamp", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_alert_county_code", "alert_logs", ["county_code"])
    op.create_index("idx_alert_sent_at", "alert_logs", ["sent_at"])
    op.create_index("idx_alert_phone_hash", "alert_logs", ["phone_number_hash"])
    
    # Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer()),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255)),
        sa.Column("changes", sa.JSON()),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_user_id", "audit_logs", ["user_id"])
    op.create_index("idx_audit_action", "audit_logs", ["action"])
    op.create_index("idx_audit_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index("idx_audit_created_at")
    op.drop_index("idx_audit_action")
    op.drop_index("idx_audit_user_id")
    op.drop_table("audit_logs")
    
    op.drop_index("idx_alert_phone_hash")
    op.drop_index("idx_alert_sent_at")
    op.drop_index("idx_alert_county_code")
    op.drop_table("alert_logs")
    
    op.drop_index("idx_risk_county_time")
    op.drop_table("risk_snapshots")
    
    op.drop_index("idx_openweather_county_time")
    op.drop_table("openweather_snapshots")
    
    op.drop_index("idx_imerg_timestamp")
    op.drop_table("imerg_snapshots")
    
    op.drop_index("idx_barometer_location")
    op.drop_index("idx_barometer_county_time")
    op.drop_index("idx_barometer_device_id")
    op.drop_table("barometer_readings")
    
    op.drop_index("idx_counties_geometry")
    op.drop_index("idx_counties_is_urban")
    op.drop_index("idx_counties_name")
    op.drop_index("idx_counties_code")
    op.drop_table("counties")
    
    op.drop_index("idx_refresh_expires_at")
    op.drop_index("idx_refresh_user_id")
    op.drop_table("refresh_tokens")
    
    op.drop_index("idx_users_is_active")
    op.drop_index("idx_users_email")
    op.drop_index("idx_users_username")
    op.drop_table("users")
