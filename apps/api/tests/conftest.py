import os
import secrets
import subprocess
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
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
from app.email import EmailMessage, get_email_provider
from app.main import create_app
from app.modules.auth.deps import SESSION_COOKIE
from app.modules.auth.models import AuthSession
from app.modules.auth.service import hash_token
from app.modules.users.models import Role, RoleAssignment, User

API_DIR = Path(__file__).parent.parent
POSTGRES_URL = "postgresql+asyncpg://residential:residential@localhost:5432"
TEST_DB_NAME = "residential_test"

type UserFactory = Callable[..., Awaitable[User]]
type LoginAs = Callable[[User], Awaitable[None]]


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


class RecordingEmailProvider:
    """Test double: captures outgoing emails instead of sending them."""

    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


@pytest.fixture
def email_outbox() -> RecordingEmailProvider:
    return RecordingEmailProvider()


@pytest.fixture
def app(
    settings: Settings, db_session: AsyncSession, email_outbox: RecordingEmailProvider
) -> FastAPI:
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_email_provider] = lambda: email_outbox
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def create_user(db_session: AsyncSession) -> UserFactory:
    async def _create(
        email: str, *roles: Role, full_name: str = "Test User", is_active: bool = True
    ) -> User:
        user = User(
            email=email,
            full_name=full_name,
            is_active=is_active,
            role_assignments=[RoleAssignment(role=role) for role in roles],
        )
        db_session.add(user)
        await db_session.flush()
        return user

    return _create


@pytest.fixture
def login_as(client: AsyncClient, db_session: AsyncSession) -> LoginAs:
    """Authenticate the test client as the given user (session created directly in db)."""

    async def _login(user: User) -> None:
        token = secrets.token_urlsafe(32)
        db_session.add(
            AuthSession(
                user_id=user.id,
                token_hash=hash_token(token),
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
        await db_session.flush()
        client.cookies.set(SESSION_COOKIE, token)

    return _login
