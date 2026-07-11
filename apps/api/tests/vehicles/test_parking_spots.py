from datetime import date, timedelta

from httpx import AsyncClient

from app.config import Settings
from app.modules.users.models import Role
from tests.conftest import LoginAs, RoleGranter, UnitFactory, UserFactory
from tests.utils import API

TODAY = date.today()


async def test_admin_assigns_spots_up_to_the_limit(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    settings: Settings,
) -> None:
    await login_as(await create_user("admin@example.com", Role.ADMIN))
    unit = await create_unit("H-1")

    for i in range(settings.parking_spots_per_unit):
        response = await client.post(
            f"{API}/units/{unit.id}/parking-spots", json={"number": f"P-{i + 1}"}
        )
        assert response.status_code == 201

    # one more than the fixed allotment is rejected
    response = await client.post(
        f"{API}/units/{unit.id}/parking-spots", json={"number": "P-99"}
    )
    assert response.status_code == 409

    spots = (await client.get(f"{API}/units/{unit.id}/parking-spots")).json()
    assert len(spots) == settings.parking_spots_per_unit


async def test_spot_numbers_are_unique_across_units(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
) -> None:
    await login_as(await create_user("admin@example.com", Role.ADMIN))
    first = await create_unit("H-1")
    second = await create_unit("H-2")

    assert (
        await client.post(
            f"{API}/units/{first.id}/parking-spots", json={"number": "P-1"}
        )
    ).status_code == 201
    assert (
        await client.post(
            f"{API}/units/{second.id}/parking-spots", json={"number": "P-1"}
        )
    ).status_code == 409


async def test_only_admin_manages_spots(
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
        f"{API}/units/{unit.id}/parking-spots", json={"number": "P-1"}
    )

    assert response.status_code == 403


async def test_members_see_spots_but_outsiders_do_not(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
) -> None:
    unit = await create_unit("H-1")
    owner = await create_user("owner@example.com")
    await grant_role(owner, Role.OWNER, unit)
    tenant = await create_user("tenant@example.com")
    await grant_role(
        tenant, Role.TENANT, unit, starts_on=TODAY, ends_on=TODAY + timedelta(days=30)
    )
    outsider = await create_user("outsider@example.com")

    for member in (owner, tenant):
        await login_as(member)
        assert (
            await client.get(f"{API}/units/{unit.id}/parking-spots")
        ).status_code == 200

    await login_as(outsider)
    assert (await client.get(f"{API}/units/{unit.id}/parking-spots")).status_code == 403


async def test_admin_removes_a_spot(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
) -> None:
    await login_as(await create_user("admin@example.com", Role.ADMIN))
    unit = await create_unit("H-1")
    spot = (
        await client.post(
            f"{API}/units/{unit.id}/parking-spots", json={"number": "P-1"}
        )
    ).json()

    assert (
        await client.delete(f"{API}/units/{unit.id}/parking-spots/{spot['id']}")
    ).status_code == 204
    assert (await client.get(f"{API}/units/{unit.id}/parking-spots")).json() == []
