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
    parking_spots_per_unit: int = (
        2  # fixed assigned spots per unit (deployment-specific)
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_app_settings(request: Request) -> Settings:
    """Settings of the running app instance (tests inject their own via create_app)."""
    return request.app.state.settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
