from decimal import Decimal

from httpx import AsyncClient

from app.modules.users.models import Role
from tests.billing.conftest import InfractionFactory
from tests.conftest import LoginAs, UserFactory

BASE = "/api/v0/infractions"


async def test_admin_creates_infraction(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    admin = await create_user("admin@example.com", Role.ADMIN)
    await login_as(admin)

    resp = await client.post(
        BASE,
        json={
            "name": "Unauthorized parking",
            "description": "Parking in another unit's spot",
            "fine_amount": "75.50",
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Unauthorized parking"
    assert Decimal(body["fine_amount"]) == Decimal("75.50")
    assert body["currency"] == "GTQ"
    assert body["is_active"] is True


async def test_non_admin_cannot_manage_catalog(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    create_infraction: InfractionFactory,
) -> None:
    infraction = await create_infraction()
    user = await create_user("resident@example.com")
    await login_as(user)

    creating = await client.post(BASE, json={"name": "Litter", "fine_amount": "10.00"})
    listing = await client.get(BASE)
    patching = await client.patch(
        f"{BASE}/{infraction.id}", json={"fine_amount": "999.00"}
    )

    assert creating.status_code == 403
    assert listing.status_code == 403
    assert patching.status_code == 403


async def test_catalog_requires_login(client: AsyncClient) -> None:
    assert (await client.get(BASE)).status_code == 401


async def test_duplicate_name_rejected(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    create_infraction: InfractionFactory,
) -> None:
    await create_infraction(name="Noise after hours")
    admin = await create_user("admin@example.com", Role.ADMIN)
    await login_as(admin)

    resp = await client.post(
        BASE, json={"name": "Noise after hours", "fine_amount": "50.00"}
    )

    assert resp.status_code == 409


async def test_validation_rules(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    admin = await create_user("admin@example.com", Role.ADMIN)
    await login_as(admin)

    zero_amount = await client.post(BASE, json={"name": "X", "fine_amount": "0"})
    empty_name = await client.post(BASE, json={"name": "", "fine_amount": "10.00"})

    assert zero_amount.status_code == 422
    assert empty_name.status_code == 422


async def test_admin_updates_infraction(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    create_infraction: InfractionFactory,
) -> None:
    infraction = await create_infraction(name="Noise", fine_amount=Decimal("50.00"))
    await create_infraction(name="Taken")
    admin = await create_user("admin@example.com", Role.ADMIN)
    await login_as(admin)

    updated = await client.patch(
        f"{BASE}/{infraction.id}", json={"fine_amount": "80.00", "is_active": False}
    )
    renamed_to_taken = await client.patch(
        f"{BASE}/{infraction.id}", json={"name": "Taken"}
    )
    unknown = await client.patch(f"{BASE}/9999", json={"is_active": True})

    assert updated.status_code == 200
    body = updated.json()
    assert Decimal(body["fine_amount"]) == Decimal("80.00")
    assert body["is_active"] is False
    assert renamed_to_taken.status_code == 409
    assert unknown.status_code == 404


async def test_admin_lists_catalog_ordered_by_name(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    create_infraction: InfractionFactory,
) -> None:
    await create_infraction(name="Speeding")
    await create_infraction(name="Litter", is_active=False)
    admin = await create_user("admin@example.com", Role.ADMIN)
    await login_as(admin)

    resp = await client.get(BASE)

    assert resp.status_code == 200
    assert [i["name"] for i in resp.json()] == ["Litter", "Speeding"]
