from functools import lru_cache
from typing import Annotated, Literal

from fastapi import Depends, Request
from pydantic_settings import BaseSettings, SettingsConfigDict

API_PREFIX = "/api/v0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_", env_file=".env", extra="ignore"
    )

    environment: Literal["local", "test", "production"] = "local"
    database_url: str = (
        "postgresql+asyncpg://residential:residential@localhost:5432/residential"
    )
    app_base_url: str = "http://localhost:8000"
    email_provider: Literal["console"] = "console"
    session_ttl_days: int = 30
    login_code_ttl_minutes: int = 10
    login_code_max_attempts: int = 5
    # Throttle for the login endpoints, per client IP per endpoint.
    auth_rate_limit_attempts: int = 10
    auth_rate_limit_window_minutes: int = 15
    # Deployment-specific policy values: generic defaults here, real values via env.
    currency: Literal["GTQ", "USD"] = "GTQ"  # currency for fees and charges
    parking_spots_per_unit: int = 2
    local_timezone: str = "UTC"  # used to evaluate recurring visit windows
    visit_expiration_hours_options: tuple[int, ...] = (1, 2, 4)
    visit_max_advance_days: int = 30
    visit_recurring_max_days: int = 366
    visit_log_retention_days: int = 365


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_app_settings(request: Request) -> Settings:
    """Settings of the running app instance (tests inject their own via create_app)."""
    return request.app.state.settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
