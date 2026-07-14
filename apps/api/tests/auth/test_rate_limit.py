import itertools

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db import get_session
from app.email import get_email_provider
from app.main import create_app
from app.rate_limit import RateLimiter
from tests.conftest import RecordingEmailProvider
from tests.utils import API

LIMIT = 3


@pytest.fixture
def app(
    settings: Settings, db_session: AsyncSession, email_outbox: RecordingEmailProvider
) -> FastAPI:
    """Same app as the global fixture, but with a tiny rate-limit budget."""
    throttled = settings.model_copy(update={"auth_rate_limit_attempts": LIMIT})
    app = create_app(throttled)
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_email_provider] = lambda: email_outbox
    return app


async def test_request_code_is_throttled(client: AsyncClient) -> None:
    payload = {"email": "anyone@example.com"}

    for _ in range(LIMIT):
        resp = await client.post(f"{API}/auth/request-code", json=payload)
        assert resp.status_code == 202

    resp = await client.post(f"{API}/auth/request-code", json=payload)
    assert resp.status_code == 429


async def test_verify_is_throttled(client: AsyncClient) -> None:
    payload = {"email": "anyone@example.com", "code": "000000"}

    for _ in range(LIMIT):
        resp = await client.post(f"{API}/auth/verify", json=payload)
        assert resp.status_code == 401

    resp = await client.post(f"{API}/auth/verify", json=payload)
    assert resp.status_code == 429


async def test_magic_link_is_throttled(client: AsyncClient) -> None:
    for _ in range(LIMIT):
        resp = await client.get(f"{API}/auth/magic", params={"token": "bogus"})
        assert resp.status_code == 401

    resp = await client.get(f"{API}/auth/magic", params={"token": "bogus"})
    assert resp.status_code == 429


async def test_endpoints_have_separate_budgets(client: AsyncClient) -> None:
    for _ in range(LIMIT + 1):
        await client.get(f"{API}/auth/magic", params={"token": "bogus"})

    resp = await client.post(
        f"{API}/auth/request-code", json={"email": "anyone@example.com"}
    )
    assert resp.status_code == 202


def test_window_slides(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = itertools.count()
    monkeypatch.setattr("app.rate_limit.time.monotonic", lambda: next(clock))
    limiter = RateLimiter(limit=2, window_seconds=5)

    assert limiter.allow("k")  # t=0
    assert limiter.allow("k")  # t=1
    assert not limiter.allow("k")  # t=2, both hits still in the window
    for _ in range(3):
        next(clock)
    assert limiter.allow("k")  # t=6, the t=0 hit has expired
