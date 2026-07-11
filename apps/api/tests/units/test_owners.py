from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.users.models import Role
from tests.conftest import LoginAs, UnitFactory, UserFactory
from tests.utils import API


async def test_admin_assigns_and_removes_owner(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    db_session: AsyncSession,
) -> None:
    admin = await create_user("admin@example.com", Role.ADMIN)
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")
    await login_as(admin)

    response = await client.post(
        f"{API}/units/{unit.id}/owners", json={"user_id": owner.id}
    )
    assert response.status_code == 201

    owners = (await client.get(f"{API}/units/{unit.id}/owners")).json()
    assert [o["email"] for o in owners] == ["owner@example.com"]

    events = list(
        await db_session.scalars(
            select(AuditLog).where(AuditLog.event == "owner_assigned")
        )
    )
    assert len(events) == 1
    assert events[0].actor_id == admin.id
    assert events[0].target_user_id == owner.id
    assert events[0].data == {"unit_id": unit.id}

    assert (
        await client.delete(f"{API}/units/{unit.id}/owners/{owner.id}")
    ).status_code == 204
    assert (await client.get(f"{API}/units/{unit.id}/owners")).json() == []
    removed = await db_session.scalar(
        select(AuditLog).where(AuditLog.event == "owner_removed")
    )
    assert removed is not None


async def test_duplicate_owner_assignment(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
) -> None:
    await login_as(await create_user("admin@example.com", Role.ADMIN))
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")

    payload = {"user_id": owner.id}
    assert (
        await client.post(f"{API}/units/{unit.id}/owners", json=payload)
    ).status_code == 201
    assert (
        await client.post(f"{API}/units/{unit.id}/owners", json=payload)
    ).status_code == 409


async def test_non_admin_cannot_assign_owners(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
) -> None:
    user = await create_user("resident@example.com")
    unit = await create_unit("H-1")
    await login_as(user)

    response = await client.post(
        f"{API}/units/{unit.id}/owners", json={"user_id": user.id}
    )

    assert response.status_code == 403


async def test_owner_sees_unit_in_mine(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role,
) -> None:
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await login_as(owner)

    mine = (await client.get(f"{API}/units/mine")).json()

    assert [u["id"] for u in mine] == [unit.id]


async def test_co_owners_both_see_the_unit(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role,
) -> None:
    first = await create_user("first@example.com")
    second = await create_user("second@example.com")
    unit = await create_unit("H-1")
    await grant_role(first, Role.OWNER, unit)
    await grant_role(second, Role.OWNER, unit)

    for owner in (first, second):
        await login_as(owner)
        assert [u["id"] for u in (await client.get(f"{API}/units/mine")).json()] == [
            unit.id
        ]
