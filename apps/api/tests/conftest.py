import os
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings
from app.db import get_session
from app.main import create_app

API_DIR = Path(__file__).parent.parent
POSTGRES_URL = "postgresql+asyncpg://residential:residential@localhost:5432"
TEST_DB_NAME = "residential_test"


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(environment="test", database_url=f"{POSTGRES_URL}/{TEST_DB_NAME}")


@pytest.fixture(scope="session")
async def _test_database(settings: Settings) -> None:
    """Create the test database if missing and migrate it to head."""
    admin = create_async_engine(
        f"{POSTGRES_URL}/postgres", isolation_level="AUTOCOMMIT"
    )
    try:
        async with admin.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": TEST_DB_NAME},
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    except OSError as exc:
        pytest.exit(
            f"PostgreSQL is not reachable ({exc}). Run: docker compose up -d postgres"
        )
    finally:
        await admin.dispose()

    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=API_DIR,
        env=os.environ | {"APP_DATABASE_URL": settings.database_url},
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="session")
async def engine(
    _test_database: None, settings: Settings
) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(settings.database_url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Session bound to an outer transaction that is always rolled back.

    Each test sees a pristine database; in-test commits become savepoints.
    """
    async with engine.connect() as conn:
        transaction = await conn.begin()
        factory = async_sessionmaker(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        async with factory() as session:
            yield session
        await transaction.rollback()


@pytest.fixture
def app(settings: Settings, db_session: AsyncSession) -> FastAPI:
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: db_session
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
