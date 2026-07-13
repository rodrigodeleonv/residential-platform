from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient

from app.modules.users.models import Role
from tests.billing.conftest import AreaFactory, OwnerFactory
from tests.conftest import LoginAs, UserFactory

TOMORROW = datetime.now(UTC).date() + timedelta(days=1)


async def book(client: AsyncClient, unit_id: int, area_id: int) -> dict[str, object]:
    resp = await client.post(
        f"/api/v0/units/{unit_id}/reservations",
        json={"area_id": area_id, "day": str(TOMORROW), "slot": "morning"},
    )
    assert resp.status_code == 201
    return resp.json()


async def test_booking_creates_pending_charge(
    client: AsyncClient,
    login_as: LoginAs,
    make_owner: OwnerFactory,
    create_area: AreaFactory,
) -> None:
    owner, unit = await make_owner()
    area = await create_area(fee=Decimal("150.00"))
    await login_as(owner)

    reservation = await book(client, unit.id, area.id)

    statement = (await client.get(f"/api/v0/units/{unit.id}/statement")).json()
    assert len(statement["pending"]) == 1
    charge = statement["pending"][0]
    assert charge["kind"] == "reservation"
    assert Decimal(charge["amount"]) == Decimal("150.00")
    assert charge["reservation_id"] == reservation["id"]
    assert f"{TOMORROW} (morning)" in charge["description"]
    assert "Clubhouse" in charge["description"]


async def test_free_area_produces_no_charge(
    client: AsyncClient,
    login_as: LoginAs,
    make_owner: OwnerFactory,
    create_area: AreaFactory,
) -> None:
    owner, unit = await make_owner()
    area = await create_area(name="Playground", fee=Decimal(0))
    await login_as(owner)

    await book(client, unit.id, area.id)

    statement = (await client.get(f"/api/v0/units/{unit.id}/statement")).json()
    assert statement["pending"] == []


async def test_canceling_reservation_voids_pending_charge(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    make_owner: OwnerFactory,
    create_area: AreaFactory,
) -> None:
    owner, unit = await make_owner()
    area = await create_area(fee=Decimal("150.00"))
    await login_as(owner)
    reservation = await book(client, unit.id, area.id)

    canceled = await client.delete(
        f"/api/v0/units/{unit.id}/reservations/{reservation['id']}"
    )
    assert canceled.status_code == 204

    statement = (await client.get(f"/api/v0/units/{unit.id}/statement")).json()
    assert statement["pending"] == []

    admin = await create_user("admin@example.com", Role.ADMIN)
    await login_as(admin)
    voided = (await client.get("/api/v0/charges?status=voided")).json()
    assert [c["reservation_id"] for c in voided] == [reservation["id"]]
    assert voided[0]["voided_at"] is not None


async def test_paid_charge_survives_admin_cancellation(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    make_owner: OwnerFactory,
    create_area: AreaFactory,
) -> None:
    owner, unit = await make_owner()
    area = await create_area(fee=Decimal("150.00"))
    await login_as(owner)
    reservation = await book(client, unit.id, area.id)

    admin = await create_user("admin@example.com", Role.ADMIN)
    await login_as(admin)
    charge = (await client.get("/api/v0/charges?status=pending")).json()[0]
    assert (await client.post(f"/api/v0/charges/{charge['id']}/pay")).status_code == 200

    canceled = await client.delete(
        f"/api/v0/units/{unit.id}/reservations/{reservation['id']}"
    )
    assert canceled.status_code == 204

    # the payment record is kept; refunds are handled outside the platform
    kept = (await client.get(f"/api/v0/charges?unit_id={unit.id}")).json()
    assert kept[0]["paid_at"] is not None
    assert kept[0]["voided_at"] is None


async def test_admin_overview_filters(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    make_owner: OwnerFactory,
    create_area: AreaFactory,
) -> None:
    owner, unit = await make_owner()
    area = await create_area(fee=Decimal("150.00"))
    await login_as(owner)
    await book(client, unit.id, area.id)

    admin = await create_user("admin@example.com", Role.ADMIN)
    await login_as(admin)
    await client.post(
        f"/api/v0/units/{unit.id}/charges",
        json={"description": "Maintenance fee", "amount": "300.00"},
    )

    everything = (await client.get("/api/v0/charges")).json()
    only_fees = (await client.get("/api/v0/charges?kind=maintenance")).json()
    other_unit = (await client.get("/api/v0/charges?unit_id=9999")).json()

    assert len(everything) == 2
    assert [c["kind"] for c in only_fees] == ["maintenance"]
    assert other_unit == []

    await login_as(owner)
    assert (await client.get("/api/v0/charges")).status_code == 403
