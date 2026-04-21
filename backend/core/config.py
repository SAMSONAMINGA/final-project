"""
Production configuration using Pydantic v2 Settings.
Centralizes all environment-based configuration with validation.

Design decisions:
- All secrets from environment only (never hardcoded)
- Type-safe configuration validation at startup
- Separate dev/test/prod profiles via ENV variable
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional


class Settings(BaseSettings):
    """Product-grade settings with validation and Ken bbox constraints."""
    
    # Service
    env: str = Field(default="development", validation_alias="ENV")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    
    # Database (AsyncPG + SQLAlchemy 2.0)
    database_url: str = Field(validation_alias="DATABASE_URL")
    sqlalchemy_echo: bool = Field(default=False, validation_alias="SQLALCHEMY_ECHO")
    
    # Redis (pub/sub + caching + rate limiting)
    redis_url: str = Field(validation_alias="REDIS_URL")
    redis_broker_url: str = Field(validation_alias="REDIS_BROKER_URL")
    
    # JWT Security (HS256, 60-min access + 7-day refresh)
    secret_key: str = Field(min_length=32, validation_alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=60, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")
    algorithm: str = Field(default="HS256", validation_alias="ALGORITHM")
    
    # CORS
    allowed_origins: str = Field(validation_alias="ALLOWED_ORIGINS")
    
    # Third-party APIs
    africas_talking_api_key: str = Field(validation_alias="AFRICAS_TALKING_API_KEY")
    africas_talking_username: str = Field(validation_alias="AFRICAS_TALKING_USERNAME")
    nasa_bearer_token: str = Field(validation_alias="NASA_BEARER_TOKEN")
    imerg_base_url: str = Field(validation_alias="IMERG_BASE_URL")
    openweather_api_key: str = Field(validation_alias="OPENWEATHER_API_KEY")
    
    # ML Models & Config
    model_path: str = Field(default="/app/models/gatv2_geoflood.onnx", validation_alias="MODEL_PATH")
    ekf_config_path: str = Field(default="/app/config/ekf_params.json", validation_alias="EKF_CONFIG_PATH")
    
    # Kenya spatial bounds (EPSG:4326) for validation
    # These enforce that all GPS/precipitation data stay within Kenya territory
    kenya_bbox_west: float = Field(default=33.9, validation_alias="KENYA_BBOX_WEST")
    kenya_bbox_south: float = Field(default=-4.7, validation_alias="KENYA_BBOX_SOUTH")
    kenya_bbox_east: float = Field(default=41.9, validation_alias="KENYA_BBOX_EAST")
    kenya_bbox_north: float = Field(default=5.0, validation_alias="KENYA_BBOX_NORTH")
    
    class Config:
        """Pydantic v2 model config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Enforce minimum entropy for production."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v
    
    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, v: str) -> list[str]:
        """Parse comma-separated CORS origins."""
        return [origin.strip() for origin in v.split(",")]
    
    @property
    def kenya_bbox(self) -> dict[str, float]:
        """Return Kenya bbox as dict for spatial lookups."""
        return {
            "west": self.kenya_bbox_west,
            "south": self.kenya_bbox_south,
            "east": self.kenya_bbox_east,
            "north": self.kenya_bbox_north,
        }
    
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.env.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.env.lower() == "development"


# Global settings singleton
settings = Settings()  # type: ignore
