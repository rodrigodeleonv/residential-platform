from datetime import date, timedelta

from httpx import AsyncClient

from app.config import Settings
from app.modules.users.models import Role
from tests.conftest import LoginAs, RoleGranter, UnitFactory, UserFactory
from tests.utils import API

TODAY = date.today()
ACTIVE = {"starts_on": TODAY, "ends_on": TODAY + timedelta(days=365)}


async def test_owner_occupant_registers_vehicle(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
) -> None:
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await login_as(owner)

    response = await client.post(
        f"{API}/units/{unit.id}/vehicles",
        json={"plate": "abc 123", "description": "Gray sedan"},
    )

    assert response.status_code == 201
    assert response.json()["plate"] == "ABC123"  # normalized


async def test_non_resident_owner_cannot_register_vehicles(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
) -> None:
    """With an active tenancy, the tenant resides — the owner loses resident actions."""
    owner = await create_user("owner@example.com")
    tenant = await create_user("tenant@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await grant_role(tenant, Role.TENANT, unit, **ACTIVE)

    await login_as(owner)
    assert (
        await client.post(f"{API}/units/{unit.id}/vehicles", json={"plate": "AAA111"})
    ).status_code == 403

    await login_as(tenant)
    assert (
        await client.post(f"{API}/units/{unit.id}/vehicles", json={"plate": "AAA111"})
    ).status_code == 201


async def test_admin_can_register_vehicles_anywhere(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
) -> None:
    await login_as(await create_user("admin@example.com", Role.ADMIN))
    unit = await create_unit("H-1")

    response = await client.post(
        f"{API}/units/{unit.id}/vehicles", json={"plate": "BBB222"}
    )

    assert response.status_code == 201


async def test_more_vehicles_than_spots_is_allowed(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
    settings: Settings,
) -> None:
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await login_as(owner)

    for i in range(settings.parking_spots_per_unit + 1):
        response = await client.post(
            f"{API}/units/{unit.id}/vehicles", json={"plate": f"CAR{i:03d}"}
        )
        assert response.status_code == 201

    vehicles = (await client.get(f"{API}/units/{unit.id}/vehicles")).json()
    assert len(vehicles) == settings.parking_spots_per_unit + 1


async def test_duplicate_plate_is_rejected(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
) -> None:
    await login_as(await create_user("admin@example.com", Role.ADMIN))
    first = await create_unit("H-1")
    second = await create_unit("H-2")

    assert (
        await client.post(f"{API}/units/{first.id}/vehicles", json={"plate": "DDD444"})
    ).status_code == 201
    # same plate, even in another unit and with different spacing/case
    assert (
        await client.post(
            f"{API}/units/{second.id}/vehicles", json={"plate": "ddd 444"}
        )
    ).status_code == 409


async def test_outsiders_cannot_see_vehicles(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
) -> None:
    unit = await create_unit("H-1")
    await login_as(await create_user("outsider@example.com"))

    assert (await client.get(f"{API}/units/{unit.id}/vehicles")).status_code == 403


async def test_resident_removes_a_vehicle(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
) -> None:
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await login_as(owner)
    vehicle = (
        await client.post(f"{API}/units/{unit.id}/vehicles", json={"plate": "EEE555"})
    ).json()

    assert (
        await client.delete(f"{API}/units/{unit.id}/vehicles/{vehicle['id']}")
    ).status_code == 204
    assert (await client.get(f"{API}/units/{unit.id}/vehicles")).json() == []
