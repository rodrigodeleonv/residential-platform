from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.units import service
from app.modules.users.models import Role, User
from tests.conftest import LoginAs, RoleGranter, UnitFactory, UserFactory
from tests.utils import API

TODAY = date.today()
CONTRACT = {"starts_on": str(TODAY), "ends_on": str(TODAY + timedelta(days=365))}


def tenant_payload(
    email: str = "tenant@example.com", **overrides: object
) -> dict[str, object]:
    return {"email": email, "full_name": "Tina Tenant", **CONTRACT, **overrides}


async def test_owner_registers_new_tenant(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
    email_outbox,
    db_session: AsyncSession,
) -> None:
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await login_as(owner)

    response = await client.post(
        f"{API}/units/{unit.id}/tenants", json=tenant_payload()
    )

    assert response.status_code == 201
    tenancy = response.json()
    assert tenancy["user"]["email"] == "tenant@example.com"

    # account created + invitation sent
    tenant = await db_session.scalar(
        select(User).where(User.email == "tenant@example.com")
    )
    assert tenant is not None
    (invitation,) = email_outbox.messages
    assert invitation.to == "tenant@example.com"

    # audited
    entry = await db_session.scalar(
        select(AuditLog).where(AuditLog.event == "tenant_registered")
    )
    assert entry is not None
    assert entry.actor_id == owner.id
    assert entry.target_user_id == tenant.id

    # tenant resides; the unit shows up in their /mine
    await login_as(tenant)
    assert [u["id"] for u in (await client.get(f"{API}/units/mine")).json()] == [
        unit.id
    ]


async def test_existing_user_can_become_tenant_without_new_invitation(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
    email_outbox,
    db_session: AsyncSession,
) -> None:
    owner = await create_user("owner@example.com")
    existing = await create_user("existing@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await login_as(owner)

    response = await client.post(
        f"{API}/units/{unit.id}/tenants", json=tenant_payload("existing@example.com")
    )

    assert response.status_code == 201
    assert response.json()["user"]["id"] == existing.id
    assert email_outbox.messages == []
    users = list(
        await db_session.scalars(
            select(User).where(User.email == "existing@example.com")
        )
    )
    assert len(users) == 1


async def test_admin_can_register_tenant_directly(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
) -> None:
    await login_as(await create_user("admin@example.com", Role.ADMIN))
    unit = await create_unit("H-1")

    response = await client.post(
        f"{API}/units/{unit.id}/tenants", json=tenant_payload()
    )

    assert response.status_code == 201


async def test_any_single_co_owner_can_register_tenants(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
) -> None:
    unit = await create_unit("H-1")
    await grant_role(await create_user("first@example.com"), Role.OWNER, unit)
    second = await create_user("second@example.com")
    await grant_role(second, Role.OWNER, unit)
    await login_as(second)

    response = await client.post(
        f"{API}/units/{unit.id}/tenants", json=tenant_payload()
    )

    assert response.status_code == 201


async def test_non_owner_cannot_manage_tenants(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
) -> None:
    unit = await create_unit("H-1")
    # a tenant of the unit cannot register other tenants either
    tenant = await create_user("tenant@example.com")
    await grant_role(
        tenant, Role.TENANT, unit, starts_on=TODAY, ends_on=TODAY + timedelta(days=30)
    )
    await login_as(tenant)

    response = await client.post(
        f"{API}/units/{unit.id}/tenants", json=tenant_payload("other@example.com")
    )

    assert response.status_code == 403


async def test_duplicate_tenancy_is_rejected(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
) -> None:
    await login_as(await create_user("admin@example.com", Role.ADMIN))
    unit = await create_unit("H-1")

    assert (
        await client.post(f"{API}/units/{unit.id}/tenants", json=tenant_payload())
    ).status_code == 201
    assert (
        await client.post(f"{API}/units/{unit.id}/tenants", json=tenant_payload())
    ).status_code == 409


async def test_invalid_contract_range_is_rejected(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
) -> None:
    await login_as(await create_user("admin@example.com", Role.ADMIN))
    unit = await create_unit("H-1")

    response = await client.post(
        f"{API}/units/{unit.id}/tenants",
        json=tenant_payload(
            starts_on=str(TODAY), ends_on=str(TODAY - timedelta(days=1))
        ),
    )

    assert response.status_code == 422


async def test_owner_extends_and_revokes_tenancy(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
    db_session: AsyncSession,
) -> None:
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await login_as(owner)
    tenancy = (
        await client.post(f"{API}/units/{unit.id}/tenants", json=tenant_payload())
    ).json()

    new_end = str(TODAY + timedelta(days=730))
    updated = await client.patch(
        f"{API}/units/{unit.id}/tenants/{tenancy['id']}", json={"ends_on": new_end}
    )
    assert updated.status_code == 200
    assert updated.json()["ends_on"] == new_end
    assert (
        await db_session.scalar(
            select(AuditLog.id).where(AuditLog.event == "tenant_updated")
        )
    ) is not None

    assert (
        await client.delete(f"{API}/units/{unit.id}/tenants/{tenancy['id']}")
    ).status_code == 204
    assert (await client.get(f"{API}/units/{unit.id}/tenants")).json() == []
    assert (
        await db_session.scalar(
            select(AuditLog.id).where(AuditLog.event == "tenant_revoked")
        )
    ) is not None


async def test_shrinking_below_start_is_rejected(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
) -> None:
    await login_as(await create_user("admin@example.com", Role.ADMIN))
    unit = await create_unit("H-1")
    tenancy = (
        await client.post(f"{API}/units/{unit.id}/tenants", json=tenant_payload())
    ).json()

    response = await client.patch(
        f"{API}/units/{unit.id}/tenants/{tenancy['id']}",
        json={"ends_on": str(TODAY - timedelta(days=1))},
    )

    assert response.status_code == 422


async def test_expired_tenancy_loses_the_unit(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
) -> None:
    tenant = await create_user("tenant@example.com")
    unit = await create_unit("H-1")
    await grant_role(
        tenant,
        Role.TENANT,
        unit,
        starts_on=TODAY - timedelta(days=365),
        ends_on=TODAY - timedelta(days=1),
    )
    await login_as(tenant)

    assert (await client.get(f"{API}/units/mine")).json() == []


async def test_occupancy_is_derived_from_active_tenancy(
    create_user: UserFactory,
    create_unit: UnitFactory,
    grant_role: RoleGranter,
    db_session: AsyncSession,
) -> None:
    """Owners-XOR-tenants: active tenants displace the owner as resident."""
    owner = await create_user("owner@example.com")
    tenant = await create_user("tenant@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)

    # no tenancy: the owner resides
    assert await service.is_resident(db_session, owner.id, unit.id)

    # active tenancy: the tenant resides, the owner does not
    tenancy = await grant_role(
        tenant, Role.TENANT, unit, starts_on=TODAY, ends_on=TODAY + timedelta(days=30)
    )
    assert await service.is_resident(db_session, tenant.id, unit.id)
    assert not await service.is_resident(db_session, owner.id, unit.id)

    # tenancy over: the owner resides again
    tenancy.ends_on = TODAY - timedelta(days=1)
    tenancy.starts_on = TODAY - timedelta(days=30)
    await db_session.flush()
    assert not await service.is_resident(db_session, tenant.id, unit.id)
    assert await service.is_resident(db_session, owner.id, unit.id)
