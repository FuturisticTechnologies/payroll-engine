"""Configuration validation pack.

The M1 review flagged that a misconfigured deployment failed late and with a
confusing error. Settings validation is eager by design, so these tests pin the
behaviour that makes it fail early instead.
"""
from __future__ import annotations

import pytest
from app.core.config import Settings, get_settings
from pydantic import ValidationError


def test_jwt_defaults_are_pinned() -> None:
    # Constructed explicitly rather than from the ambient environment: the test
    # session sets APP_ENV/DATABASE_URL, so bare Settings() is not a default.
    settings = Settings(APP_ENV="development")
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_access_token_expire_minutes == 30
    assert settings.jwt_refresh_token_expire_days == 7


def test_cors_origins_are_split_and_stripped() -> None:
    settings = Settings(APP_CORS_ORIGINS="http://a.test , http://b.test ,")
    assert settings.cors_origins_list == ["http://a.test", "http://b.test"]


def test_empty_cors_origins_yields_empty_list() -> None:
    assert Settings(APP_CORS_ORIGINS="   ").cors_origins_list == []


def test_short_secret_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(APP_SECRET_KEY="too-short")


def test_placeholder_secret_is_rejected_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            APP_SECRET_KEY="change-me-in-production-this-must-be-at-least-32-chars",
        )


def test_placeholder_secret_is_tolerated_outside_production() -> None:
    settings = Settings(
        APP_ENV="development",
        APP_SECRET_KEY="change-me-in-production-this-must-be-at-least-32-chars",
    )
    assert settings.app_env == "development"


def test_unknown_environment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(APP_ENV="qa")


def test_short_admin_password_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(LOCAL_ADMIN_PASSWORD="short")


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()
