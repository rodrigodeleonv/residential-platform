from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_", env_file=".env", extra="ignore"
    )

    environment: Literal["local", "test", "production"] = "local"
    database_url: str = (
        "postgresql+asyncpg://residential:residential@localhost:5432/residential"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
