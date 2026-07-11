from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.users.models import Role
from tests.conftest import LoginAs, RecordingEmailProvider, UserFactory
from tests.utils import API, extract_code


async def test_me_requires_auth(client: AsyncClient) -> None:
    assert (await client.get(f"{API}/users/me")).status_code == 401


async def test_me_returns_current_user_with_roles(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    user = await create_user("admin@example.com", Role.ADMIN, full_name="Ada Admin")
    await login_as(user)

    body = (await client.get(f"{API}/users/me")).json()

    assert body["email"] == "admin@example.com"
    assert body["full_name"] == "Ada Admin"
    assert body["roles"] == ["admin"]


async def test_admin_creates_user_and_invitation_allows_login(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    email_outbox: RecordingEmailProvider,
    db_session: AsyncSession,
) -> None:
    admin = await create_user("admin@example.com", Role.ADMIN)
    await login_as(admin)

    response = await client.post(
        f"{API}/users",
        json={
            "email": "guard@example.com",
            "full_name": "Gate Guard",
            "roles": ["guard"],
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["roles"] == ["guard"]

    (invitation,) = email_outbox.messages
    assert invitation.to == "guard@example.com"

    audit_entry = await db_session.scalar(
        select(AuditLog).where(AuditLog.event == "user_created")
    )
    assert audit_entry is not None
    assert audit_entry.actor_id == admin.id
    assert audit_entry.target_user_id == created["id"]
    assert audit_entry.data == {"roles": ["guard"]}

    # The invited user can log in with the emailed code.
    code = extract_code(invitation.body)
    verify = await client.post(
        f"{API}/auth/verify", json={"email": "guard@example.com", "code": code}
    )
    assert verify.status_code == 200
    assert (await client.get(f"{API}/users/me")).json()["email"] == "guard@example.com"


async def test_create_user_without_invitation_sends_no_email(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    email_outbox: RecordingEmailProvider,
) -> None:
    await login_as(await create_user("admin@example.com", Role.ADMIN))

    response = await client.post(
        f"{API}/users",
        json={
            "email": "new@example.com",
            "full_name": "New User",
            "send_invitation": False,
        },
    )

    assert response.status_code == 201
    assert email_outbox.messages == []


async def test_duplicate_email_is_rejected(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    await login_as(await create_user("admin@example.com", Role.ADMIN))
    await create_user("taken@example.com")

    response = await client.post(
        f"{API}/users", json={"email": "taken@example.com", "full_name": "Copy Cat"}
    )

    assert response.status_code == 409


async def test_non_admin_cannot_create_users(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    await login_as(await create_user("resident@example.com"))

    response = await client.post(
        f"{API}/users", json={"email": "x@example.com", "full_name": "X"}
    )

    assert response.status_code == 403


async def test_anonymous_cannot_create_users(client: AsyncClient) -> None:
    response = await client.post(
        f"{API}/users", json={"email": "x@example.com", "full_name": "X"}
    )

    assert response.status_code == 401


async def test_list_users_is_admin_only(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    resident = await create_user("resident@example.com")
    await login_as(resident)
    assert (await client.get(f"{API}/users")).status_code == 403

    admin = await create_user("admin@example.com", Role.ADMIN)
    await login_as(admin)
    response = await client.get(f"{API}/users")
    assert response.status_code == 200
    assert [user["email"] for user in response.json()] == [
        "resident@example.com",
        "admin@example.com",
    ]
