"""Application settings.

Pydantic-settings reads from environment variables (and a `.env` file when
running natively). Validation is eager so misconfiguration fails fast on boot.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production", "test"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- App ----------
    app_env: Environment = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_secret_key: str = Field(
        default="change-me-in-production-this-must-be-at-least-32-chars",
        alias="APP_SECRET_KEY",
        min_length=32,
    )
    app_cors_origins: str = Field(
        default="http://localhost:4200",
        alias="APP_CORS_ORIGINS",
    )
    local_admin_email: str = Field(
        default="admin@payrollfuturistic.co.uk",
        alias="LOCAL_ADMIN_EMAIL",
    )
    local_admin_password: str = Field(
        default="Admin12345!",
        alias="LOCAL_ADMIN_PASSWORD",
        min_length=8,
    )

    # ---------- Database ----------
    database_url: str = Field(
        default="postgresql+asyncpg://payroll:payroll_dev_pwd@localhost:5432/payroll",
        alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg2://payroll:payroll_dev_pwd@localhost:5432/payroll",
        alias="DATABASE_URL_SYNC",
    )

    # ---------- Redis ----------
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # ---------- JWT ----------
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )

    # ---------- HMRC ----------
    hmrc_base_url: str = Field(
        default="https://test-api.service.hmrc.gov.uk",
        alias="HMRC_BASE_URL",
    )
    hmrc_client_id: str = Field(default="", alias="HMRC_CLIENT_ID")
    hmrc_client_secret: str = Field(default="", alias="HMRC_CLIENT_SECRET")

    # ---------- Derived ----------
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.app_cors_origins.split(",") if o.strip()]

    @field_validator("app_secret_key")
    @classmethod
    def _secret_not_default_in_prod(cls, v: str, info) -> str:  # type: ignore[no-untyped-def]
        env = (info.data or {}).get("app_env")
        if env == "production" and v.startswith("change-me"):
            raise ValueError("APP_SECRET_KEY must be overridden in production")
        return v


@lru_cache
def get_settings() -> Settings:
    """Cached singleton accessor."""
    return Settings()
