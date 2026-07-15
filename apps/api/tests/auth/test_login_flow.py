from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.audit.models import AuditLog
from app.modules.auth.models import LoginCode
from tests.conftest import LoginAs, RecordingEmailProvider, UserFactory
from tests.utils import API, extract_code, extract_magic_token, request_code, wrong_code


async def test_request_code_emails_a_code(
    client: AsyncClient, create_user: UserFactory, email_outbox: RecordingEmailProvider
) -> None:
    await create_user("resident@example.com")

    await request_code(client, "resident@example.com")

    (message,) = email_outbox.messages
    assert message.to == "resident@example.com"
    assert extract_code(message.body)
    assert extract_magic_token(message.body)


async def test_request_code_for_unknown_email_is_silent(
    client: AsyncClient, email_outbox: RecordingEmailProvider
) -> None:
    await request_code(client, "ghost@example.com")

    assert email_outbox.messages == []


async def test_inactive_user_cannot_request_code(
    client: AsyncClient, create_user: UserFactory, email_outbox: RecordingEmailProvider
) -> None:
    await create_user("gone@example.com", is_active=False)

    await request_code(client, "gone@example.com")

    assert email_outbox.messages == []


async def test_login_with_code(
    client: AsyncClient, create_user: UserFactory, email_outbox: RecordingEmailProvider
) -> None:
    await create_user("resident@example.com")
    await request_code(client, "resident@example.com")
    code = extract_code(email_outbox.messages[0].body)

    response = await client.post(
        f"{API}/auth/verify", json={"email": "resident@example.com", "code": code}
    )

    assert response.status_code == 200
    me = await client.get(f"{API}/users/me")
    assert me.status_code == 200
    assert me.json()["email"] == "resident@example.com"


async def test_wrong_code_is_rejected(
    client: AsyncClient, create_user: UserFactory, email_outbox: RecordingEmailProvider
) -> None:
    await create_user("resident@example.com")
    await request_code(client, "resident@example.com")
    code = extract_code(email_outbox.messages[0].body)

    response = await client.post(
        f"{API}/auth/verify",
        json={"email": "resident@example.com", "code": wrong_code(code)},
    )

    assert response.status_code == 401
    assert (await client.get(f"{API}/users/me")).status_code == 401


async def test_code_is_single_use(
    client: AsyncClient, create_user: UserFactory, email_outbox: RecordingEmailProvider
) -> None:
    await create_user("resident@example.com")
    await request_code(client, "resident@example.com")
    code = extract_code(email_outbox.messages[0].body)
    payload = {"email": "resident@example.com", "code": code}

    assert (await client.post(f"{API}/auth/verify", json=payload)).status_code == 200
    assert (await client.post(f"{API}/auth/verify", json=payload)).status_code == 401


async def test_expired_code_is_rejected(
    client: AsyncClient,
    create_user: UserFactory,
    email_outbox: RecordingEmailProvider,
    db_session: AsyncSession,
) -> None:
    await create_user("resident@example.com")
    await request_code(client, "resident@example.com")
    code = extract_code(email_outbox.messages[0].body)
    await db_session.execute(
        update(LoginCode).values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
    )

    response = await client.post(
        f"{API}/auth/verify", json={"email": "resident@example.com", "code": code}
    )

    assert response.status_code == 401


async def test_attempt_limit_blocks_even_the_correct_code(
    client: AsyncClient,
    create_user: UserFactory,
    email_outbox: RecordingEmailProvider,
    settings: Settings,
) -> None:
    await create_user("resident@example.com")
    await request_code(client, "resident@example.com")
    code = extract_code(email_outbox.messages[0].body)

    for _ in range(settings.login_code_max_attempts):
        response = await client.post(
            f"{API}/auth/verify",
            json={"email": "resident@example.com", "code": wrong_code(code)},
        )
        assert response.status_code == 401

    response = await client.post(
        f"{API}/auth/verify", json={"email": "resident@example.com", "code": code}
    )
    assert response.status_code == 401


async def test_magic_link_login(
    client: AsyncClient, create_user: UserFactory, email_outbox: RecordingEmailProvider
) -> None:
    await create_user("resident@example.com")
    await request_code(client, "resident@example.com")
    token = extract_magic_token(email_outbox.messages[0].body)

    response = await client.get(f"{API}/auth/magic", params={"token": token})

    # The email link lands the logged-in user on the app itself.
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert (await client.get(f"{API}/users/me")).status_code == 200


async def test_logout(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    user = await create_user("resident@example.com")
    await login_as(user)
    assert (await client.get(f"{API}/users/me")).status_code == 200

    assert (await client.post(f"{API}/auth/logout")).status_code == 204

    assert (await client.get(f"{API}/users/me")).status_code == 401


async def test_login_and_logout_are_audited(
    client: AsyncClient,
    create_user: UserFactory,
    email_outbox: RecordingEmailProvider,
    db_session: AsyncSession,
) -> None:
    user = await create_user("resident@example.com")
    await request_code(client, "resident@example.com")
    code = extract_code(email_outbox.messages[0].body)
    await client.post(
        f"{API}/auth/verify", json={"email": "resident@example.com", "code": code}
    )
    await client.post(f"{API}/auth/logout")

    events = list(
        await db_session.scalars(
            select(AuditLog.event).where(AuditLog.actor_id == user.id)
        )
    )

    assert events == ["login", "logout"]
