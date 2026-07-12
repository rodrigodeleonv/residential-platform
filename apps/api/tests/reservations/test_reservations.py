from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reservations.models import Reservation, TimeSlot
from app.modules.users.models import Role
from tests.conftest import LoginAs, RoleGranter, UnitFactory, UserFactory
from tests.reservations.conftest import AreaFactory, ResidentFactory
from tests.utils import API

TODAY = datetime.now(UTC).date()
TOMORROW = TODAY + timedelta(days=1)
YESTERDAY = TODAY - timedelta(days=1)
# starts_on two days back so timezone skew (UTC vs local dates) can't matter
ACTIVE_TENANCY = {
    "starts_on": TODAY - timedelta(days=2),
    "ends_on": TODAY + timedelta(days=365),
}


def booking(
    area_id: int, slot: str = "morning", day: date = TOMORROW
) -> dict[str, int | str]:
    return {"area_id": area_id, "day": str(day), "slot": slot}


async def test_resident_books_a_slot(
    client: AsyncClient,
    make_resident: ResidentFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    user, unit = await make_resident()
    area = await create_area("Gym", fee=Decimal("100.00"))
    await login_as(user)

    response = await client.post(
        f"{API}/units/{unit.id}/reservations", json=booking(area.id)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["day"] == str(TOMORROW)
    assert body["slot"] == "morning"
    assert Decimal(body["fee"]) == Decimal("100.00")
    assert body["currency"] == "GTQ"
    assert body["canceled_at"] is None


async def test_fee_is_snapshotted_at_booking_time(
    client: AsyncClient,
    make_resident: ResidentFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
    db_session: AsyncSession,
) -> None:
    user, unit = await make_resident()
    area = await create_area("Gym", fee=Decimal("100"))
    await login_as(user)
    assert (
        await client.post(f"{API}/units/{unit.id}/reservations", json=booking(area.id))
    ).status_code == 201

    area.fee = Decimal("999")
    await db_session.flush()

    listed = (await client.get(f"{API}/units/{unit.id}/reservations")).json()
    assert Decimal(listed[0]["fee"]) == Decimal("100.00")


async def test_one_user_may_book_all_slots_of_a_day(
    client: AsyncClient,
    make_resident: ResidentFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    user, unit = await make_resident()
    area = await create_area("Gym")
    await login_as(user)

    for slot in TimeSlot:
        response = await client.post(
            f"{API}/units/{unit.id}/reservations", json=booking(area.id, slot)
        )
        assert response.status_code == 201


async def test_duplicate_slot_booking_is_rejected(
    client: AsyncClient,
    make_resident: ResidentFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    user, unit = await make_resident()
    area = await create_area("Gym", capacity=5)
    await login_as(user)

    payload = booking(area.id)
    assert (
        await client.post(f"{API}/units/{unit.id}/reservations", json=payload)
    ).status_code == 201
    assert (
        await client.post(f"{API}/units/{unit.id}/reservations", json=payload)
    ).status_code == 409


async def test_capacity_limits_parallel_bookings(
    client: AsyncClient,
    make_resident: ResidentFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    area = await create_area("Gym", capacity=1)
    first_user, first_unit = await make_resident("first@example.com", "H-1")
    second_user, second_unit = await make_resident("second@example.com", "H-2")

    await login_as(first_user)
    assert (
        await client.post(
            f"{API}/units/{first_unit.id}/reservations", json=booking(area.id)
        )
    ).status_code == 201

    await login_as(second_user)
    assert (
        await client.post(
            f"{API}/units/{second_unit.id}/reservations", json=booking(area.id)
        )
    ).status_code == 409
    # a different slot of the same day is still free
    assert (
        await client.post(
            f"{API}/units/{second_unit.id}/reservations",
            json=booking(area.id, "afternoon"),
        )
    ).status_code == 201


async def test_canceling_frees_the_slot(
    client: AsyncClient,
    make_resident: ResidentFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    area = await create_area("Gym", capacity=1)
    first_user, first_unit = await make_resident("first@example.com", "H-1")
    second_user, second_unit = await make_resident("second@example.com", "H-2")

    await login_as(first_user)
    reservation = (
        await client.post(
            f"{API}/units/{first_unit.id}/reservations", json=booking(area.id)
        )
    ).json()
    assert (
        await client.delete(
            f"{API}/units/{first_unit.id}/reservations/{reservation['id']}"
        )
    ).status_code == 204
    # canceling again: the active reservation no longer exists
    assert (
        await client.delete(
            f"{API}/units/{first_unit.id}/reservations/{reservation['id']}"
        )
    ).status_code == 404

    availability = (
        await client.get(
            f"{API}/areas/{area.id}/availability", params={"day": str(TOMORROW)}
        )
    ).json()
    assert all(entry["available"] == 1 for entry in availability)

    await login_as(second_user)
    assert (
        await client.post(
            f"{API}/units/{second_unit.id}/reservations", json=booking(area.id)
        )
    ).status_code == 201


async def test_booking_an_ended_slot_is_rejected(
    client: AsyncClient,
    make_resident: ResidentFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    user, unit = await make_resident()
    area = await create_area("Gym")
    await login_as(user)

    response = await client.post(
        f"{API}/units/{unit.id}/reservations",
        json=booking(area.id, "evening", YESTERDAY),
    )

    assert response.status_code == 422


async def test_inactive_area_cannot_be_booked(
    client: AsyncClient,
    make_resident: ResidentFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    user, unit = await make_resident()
    area = await create_area("Gym", is_active=False)
    await login_as(user)

    assert (
        await client.post(f"{API}/units/{unit.id}/reservations", json=booking(area.id))
    ).status_code == 409


async def test_unknown_area_is_rejected(
    client: AsyncClient, make_resident: ResidentFactory, login_as: LoginAs
) -> None:
    user, unit = await make_resident()
    await login_as(user)

    assert (
        await client.post(f"{API}/units/{unit.id}/reservations", json=booking(9999))
    ).status_code == 404


async def test_non_resident_owner_cannot_book(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    grant_role: RoleGranter,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    """With an active tenancy, the tenant resides — the owner loses resident actions."""
    owner = await create_user("owner@example.com")
    tenant = await create_user("tenant@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await grant_role(tenant, Role.TENANT, unit, **ACTIVE_TENANCY)
    area = await create_area("Gym")

    await login_as(owner)
    assert (
        await client.post(f"{API}/units/{unit.id}/reservations", json=booking(area.id))
    ).status_code == 403

    await login_as(tenant)
    assert (
        await client.post(f"{API}/units/{unit.id}/reservations", json=booking(area.id))
    ).status_code == 201


async def test_outsiders_cannot_see_unit_reservations(
    client: AsyncClient,
    make_resident: ResidentFactory,
    create_user: UserFactory,
    login_as: LoginAs,
) -> None:
    _, unit = await make_resident()
    await login_as(await create_user("outsider@example.com"))

    assert (await client.get(f"{API}/units/{unit.id}/reservations")).status_code == 403


async def test_only_creator_or_admin_cancels(
    client: AsyncClient,
    make_resident: ResidentFactory,
    create_user: UserFactory,
    grant_role: RoleGranter,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    user, unit = await make_resident()
    co_owner = await create_user("co-owner@example.com")
    await grant_role(co_owner, Role.OWNER, unit)
    area = await create_area("Gym")

    await login_as(user)
    reservation = (
        await client.post(f"{API}/units/{unit.id}/reservations", json=booking(area.id))
    ).json()
    url = f"{API}/units/{unit.id}/reservations/{reservation['id']}"

    await login_as(co_owner)
    assert (await client.delete(url)).status_code == 403

    await login_as(await create_user("admin@example.com", Role.ADMIN))
    assert (await client.delete(url)).status_code == 204


async def test_cancel_after_slot_start_is_rejected(
    client: AsyncClient,
    make_resident: ResidentFactory,
    create_user: UserFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
    db_session: AsyncSession,
) -> None:
    user, unit = await make_resident()
    area = await create_area("Gym")
    reservation = Reservation(
        area_id=area.id,
        unit_id=unit.id,
        user_id=user.id,
        day=YESTERDAY,
        slot=TimeSlot.MORNING,
        fee=Decimal(0),
    )
    db_session.add(reservation)
    await db_session.flush()
    url = f"{API}/units/{unit.id}/reservations/{reservation.id}"

    await login_as(user)
    assert (await client.delete(url)).status_code == 409

    # admins may cancel anytime
    await login_as(await create_user("admin@example.com", Role.ADMIN))
    assert (await client.delete(url)).status_code == 204


async def test_admin_lists_all_reservations(
    client: AsyncClient,
    make_resident: ResidentFactory,
    create_user: UserFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    first_user, first_unit = await make_resident("first@example.com", "H-1")
    second_user, second_unit = await make_resident("second@example.com", "H-2")
    gym = await create_area("Gym")
    pool = await create_area("Pool")

    await login_as(first_user)
    await client.post(f"{API}/units/{first_unit.id}/reservations", json=booking(gym.id))
    await login_as(second_user)
    await client.post(
        f"{API}/units/{second_unit.id}/reservations",
        json=booking(pool.id, "afternoon"),
    )
    assert (await client.get(f"{API}/reservations")).status_code == 403  # not admin

    await login_as(await create_user("admin@example.com", Role.ADMIN))
    assert len((await client.get(f"{API}/reservations")).json()) == 2
    by_area = (
        await client.get(f"{API}/reservations", params={"area_id": gym.id})
    ).json()
    assert [r["area_id"] for r in by_area] == [gym.id]
    by_day = (
        await client.get(f"{API}/reservations", params={"day": str(TOMORROW)})
    ).json()
    assert len(by_day) == 2


async def test_availability_reflects_bookings(
    client: AsyncClient,
    make_resident: ResidentFactory,
    login_as: LoginAs,
    create_area: AreaFactory,
) -> None:
    user, unit = await make_resident()
    area = await create_area("Gym", capacity=2)
    await login_as(user)
    await client.post(f"{API}/units/{unit.id}/reservations", json=booking(area.id))

    availability = {
        entry["slot"]: entry
        for entry in (
            await client.get(
                f"{API}/areas/{area.id}/availability", params={"day": str(TOMORROW)}
            )
        ).json()
    }

    assert availability["morning"] == {
        "slot": "morning",
        "capacity": 2,
        "booked": 1,
        "available": 1,
    }
    assert availability["afternoon"]["available"] == 2
