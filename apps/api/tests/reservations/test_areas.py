from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient

from app.modules.users.models import Role
from tests.conftest import LoginAs, UserFactory
from tests.reservations.conftest import AreaFactory
from tests.utils import API

TOMORROW = datetime.now(UTC).date() + timedelta(days=1)


async def test_admin_creates_area(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    await login_as(await create_user("admin@example.com", Role.ADMIN))

    response = await client.post(
        f"{API}/areas",
        json={
            "name": "Pool",
            "description": "Main pool",
            "capacity": 2,
            "fee": "150.00",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["capacity"] == 2
    assert Decimal(body["fee"]) == Decimal("150.00")
    assert body["currency"] == "GTQ"
    assert body["is_active"] is True


async def test_only_admins_manage_areas(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    area = await create_area("Gym")
    await login_as(await create_user("resident@example.com"))

    assert (await client.post(f"{API}/areas", json={"name": "Pool"})).status_code == 403
    assert (
        await client.patch(f"{API}/areas/{area.id}", json={"fee": "10"})
    ).status_code == 403


async def test_duplicate_area_name_is_rejected(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    await create_area("Pool")
    await login_as(await create_user("admin@example.com", Role.ADMIN))

    assert (await client.post(f"{API}/areas", json={"name": "Pool"})).status_code == 409


async def test_area_validation(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    await login_as(await create_user("admin@example.com", Role.ADMIN))

    for bad in ({"name": "Pool", "capacity": 0}, {"name": "Pool", "fee": "-1"}):
        assert (await client.post(f"{API}/areas", json=bad)).status_code == 422


async def test_admin_updates_area(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    area = await create_area("Gym", fee=Decimal("50"))
    await login_as(await create_user("admin@example.com", Role.ADMIN))

    response = await client.patch(
        f"{API}/areas/{area.id}", json={"fee": "75.50", "is_active": False}
    )

    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["fee"]) == Decimal("75.50")
    assert body["is_active"] is False


async def test_rename_to_taken_name_is_rejected(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    await create_area("Pool")
    area = await create_area("Gym")
    await login_as(await create_user("admin@example.com", Role.ADMIN))

    assert (
        await client.patch(f"{API}/areas/{area.id}", json={"name": "Pool"})
    ).status_code == 409


async def test_residents_see_only_active_areas(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    await create_area("Gym")
    await create_area("Sauna", is_active=False)

    await login_as(await create_user("resident@example.com"))
    names = [area["name"] for area in (await client.get(f"{API}/areas")).json()]
    assert names == ["Gym"]

    await login_as(await create_user("admin@example.com", Role.ADMIN))
    names = [area["name"] for area in (await client.get(f"{API}/areas")).json()]
    assert names == ["Gym", "Sauna"]


async def test_area_endpoints_require_login(
    client: AsyncClient, create_area: AreaFactory
) -> None:
    area = await create_area("Gym")

    assert (await client.get(f"{API}/areas")).status_code == 401
    assert (
        await client.get(
            f"{API}/areas/{area.id}/availability", params={"day": str(TOMORROW)}
        )
    ).status_code == 401


async def test_availability_lists_all_slots(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    area = await create_area("Gym", capacity=2)
    await login_as(await create_user("resident@example.com"))

    response = await client.get(
        f"{API}/areas/{area.id}/availability", params={"day": str(TOMORROW)}
    )

    assert response.status_code == 200
    slots = response.json()
    assert [entry["slot"] for entry in slots] == ["morning", "afternoon", "evening"]
    assert all(
        entry["capacity"] == 2 and entry["booked"] == 0 and entry["available"] == 2
        for entry in slots
    )
    assert (
        await client.get(
            f"{API}/areas/9999/availability", params={"day": str(TOMORROW)}
        )
    ).status_code == 404
