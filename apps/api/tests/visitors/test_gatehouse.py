from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.audit.models import AuditLog
from app.modules.units.models import VisitorParkingSpot
from app.modules.users.models import Role, User
from app.modules.visitors import service
from app.modules.visitors.models import VisitPreRegistration
from tests.conftest import LoginAs, RoleGranter, UnitFactory, UserFactory
from tests.utils import API

TODAY = date.today()
ACTIVE = {"starts_on": TODAY, "ends_on": TODAY + timedelta(days=365)}


def active_one_off(settings: Settings) -> dict[str, object]:
    """A one-off pre-registration whose window is open right now."""
    return {
        "visitor_name": "Expected Guest",
        "kind": "one_off",
        "expiration_hours": settings.visit_expiration_hours_options[0],
        "starts_at": datetime.now(UTC).isoformat(),
    }


@pytest.fixture
async def guard(create_user: UserFactory) -> User:
    return await create_user("guard@example.com", Role.GUARD)


async def test_unit_card_shows_restricted_subset_for_actual_residents(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
    guard: User,
    db_session: AsyncSession,
) -> None:
    owner = await create_user("owner@example.com", full_name="Olivia Owner")
    tenant = await create_user("tenant@example.com", full_name="Tina Tenant")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await grant_role(tenant, Role.TENANT, unit, **ACTIVE)
    db_session.add_all([])

    await login_as(guard)
    card = (await client.get(f"{API}/gatehouse/units/{unit.id}")).json()

    # rented unit: the guard sees the tenant (who resides), not the owner
    assert [r["full_name"] for r in card["residents"]] == ["Tina Tenant"]
    assert card["number"] == "H-1"
    # the card never includes emails or ids of residents
    assert all(set(r) == {"full_name", "phone"} for r in card["residents"])


async def test_unit_card_requires_guard_role(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
) -> None:
    unit = await create_unit("H-1")
    await login_as(await create_user("resident@example.com"))

    assert (await client.get(f"{API}/gatehouse/units/{unit.id}")).status_code == 403


async def test_guard_sees_prereg_only_within_window(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
    guard: User,
    settings: Settings,
    db_session: AsyncSession,
) -> None:
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await login_as(owner)
    created = (
        await client.post(
            f"{API}/units/{unit.id}/preregistrations", json=active_one_off(settings)
        )
    ).json()
    # a second one that starts tomorrow: outside the window today
    tomorrow = active_one_off(settings) | {
        "starts_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()
    }
    await client.post(f"{API}/units/{unit.id}/preregistrations", json=tomorrow)

    await login_as(guard)
    active = (
        await client.get(f"{API}/gatehouse/units/{unit.id}/active-preregistrations")
    ).json()
    assert [p["id"] for p in active] == [created["id"]]

    # once its window passes, it disappears from the gatehouse view
    await db_session.execute(
        update(VisitPreRegistration)
        .where(VisitPreRegistration.id == created["id"])
        .values(
            starts_at=datetime.now(UTC)
            - timedelta(hours=created["expiration_hours"] + 1)
        )
    )
    active = (
        await client.get(f"{API}/gatehouse/units/{unit.id}/active-preregistrations")
    ).json()
    assert active == []


async def test_recurring_window_matches_weekday_and_time(settings: Settings) -> None:
    now = datetime.now(UTC)
    window_open = now - timedelta(minutes=30)  # may fall on yesterday around midnight
    prereg = VisitPreRegistration(
        unit_id=1,
        visitor_name="X",
        kind="recurring",
        expiration_hours=settings.visit_expiration_hours_options[0],
        weekday=window_open.weekday(),
        time_of_day=window_open.time(),
        valid_from=window_open.date() - timedelta(days=7),
        valid_until=window_open.date() + timedelta(days=7),
    )
    assert service.is_active_at(prereg, now, settings)

    prereg.weekday = (window_open.weekday() + 3) % 7
    assert not service.is_active_at(prereg, now, settings)


async def test_flow_b_entry_with_valid_preregistration(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
    guard: User,
    settings: Settings,
    db_session: AsyncSession,
) -> None:
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await login_as(owner)
    prereg = (
        await client.post(
            f"{API}/units/{unit.id}/preregistrations", json=active_one_off(settings)
        )
    ).json()

    await login_as(guard)
    spot = VisitorParkingSpot(number="V-1")
    db_session.add(spot)
    await db_session.flush()

    response = await client.post(
        f"{API}/gatehouse/visits",
        json={
            "unit_id": unit.id,
            "visitor_name": "Expected Guest",
            "visitor_plate": "vis 123",
            "visitor_spot_id": spot.id,
            "preregistration_id": prereg["id"],
        },
    )

    assert response.status_code == 201
    visit = response.json()
    assert visit["preregistration_id"] == prereg["id"]
    assert visit["guard_id"] == guard.id
    assert visit["exited_at"] is None

    entry = await db_session.scalar(
        select(AuditLog).where(AuditLog.event == "visitor_entry")
    )
    assert entry is not None
    assert entry.actor_id == guard.id


async def test_flow_b_rejects_inactive_preregistration(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
    guard: User,
    settings: Settings,
) -> None:
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await login_as(owner)
    tomorrow = active_one_off(settings) | {
        "starts_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()
    }
    prereg = (
        await client.post(f"{API}/units/{unit.id}/preregistrations", json=tomorrow)
    ).json()

    await login_as(guard)
    response = await client.post(
        f"{API}/gatehouse/visits",
        json={
            "unit_id": unit.id,
            "visitor_name": "Early Bird",
            "preregistration_id": prereg["id"],
        },
    )

    assert response.status_code == 422


async def test_flow_a_entry_authorized_by_resident(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
    guard: User,
    db_session: AsyncSession,
) -> None:
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)

    await login_as(guard)
    response = await client.post(
        f"{API}/gatehouse/visits",
        json={
            "unit_id": unit.id,
            "visitor_name": "Surprise Guest",
            "authorized_by_user_id": owner.id,
        },
    )

    assert response.status_code == 201
    assert response.json()["authorized_by_id"] == owner.id

    entry = await db_session.scalar(
        select(AuditLog).where(AuditLog.event == "visitor_entry")
    )
    assert entry is not None
    assert entry.target_user_id == owner.id  # who authorized is audited


async def test_flow_a_rejects_non_resident_authorizer(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
    guard: User,
) -> None:
    owner = await create_user("owner@example.com")
    tenant = await create_user("tenant@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await grant_role(tenant, Role.TENANT, unit, **ACTIVE)  # owner no longer resides

    await login_as(guard)
    response = await client.post(
        f"{API}/gatehouse/visits",
        json={
            "unit_id": unit.id,
            "visitor_name": "Guest",
            "authorized_by_user_id": owner.id,
        },
    )

    assert response.status_code == 422


async def test_entry_requires_exactly_one_authorization(
    client: AsyncClient,
    create_unit: UnitFactory,
    login_as: LoginAs,
    guard: User,
) -> None:
    unit = await create_unit("H-1")
    await login_as(guard)

    response = await client.post(
        f"{API}/gatehouse/visits",
        json={"unit_id": unit.id, "visitor_name": "Nobody Approved"},
    )

    assert response.status_code == 422


async def test_occupied_visitor_spot_is_rejected(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
    guard: User,
    db_session: AsyncSession,
) -> None:
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    spot = VisitorParkingSpot(number="V-1")
    db_session.add(spot)
    await db_session.flush()
    await login_as(guard)

    payload = {
        "unit_id": unit.id,
        "visitor_name": "First Car",
        "visitor_spot_id": spot.id,
        "authorized_by_user_id": owner.id,
    }
    assert (
        await client.post(f"{API}/gatehouse/visits", json=payload)
    ).status_code == 201
    # cone is out: same spot for a second open visit is rejected
    assert (
        await client.post(f"{API}/gatehouse/visits", json=payload)
    ).status_code == 409


async def test_exit_flow_and_open_visits(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
    guard: User,
) -> None:
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await login_as(guard)
    visit = (
        await client.post(
            f"{API}/gatehouse/visits",
            json={
                "unit_id": unit.id,
                "visitor_name": "G",
                "authorized_by_user_id": owner.id,
            },
        )
    ).json()

    open_visits = (
        await client.get(f"{API}/gatehouse/visits", params={"open_only": True})
    ).json()
    assert [v["id"] for v in open_visits] == [visit["id"]]

    exited = await client.post(f"{API}/gatehouse/visits/{visit['id']}/exit")
    assert exited.status_code == 200
    assert exited.json()["exited_at"] is not None

    # exit AND entry both recorded; double exit rejected; nothing open anymore
    assert (
        await client.post(f"{API}/gatehouse/visits/{visit['id']}/exit")
    ).status_code == 409
    assert (
        await client.get(f"{API}/gatehouse/visits", params={"open_only": True})
    ).json() == []


async def test_retention_purge(
    create_user: UserFactory,
    create_unit: UnitFactory,
    grant_role: RoleGranter,
    guard: User,
    settings: Settings,
    db_session: AsyncSession,
) -> None:
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    from app.modules.visitors.models import VisitLog

    old = VisitLog(
        unit_id=unit.id,
        visitor_name="Ancient Guest",
        guard_id=guard.id,
        authorized_by_id=owner.id,
        entered_at=datetime.now(UTC)
        - timedelta(days=settings.visit_log_retention_days + 5),
        exited_at=datetime.now(UTC)
        - timedelta(days=settings.visit_log_retention_days + 5),
    )
    recent = VisitLog(
        unit_id=unit.id,
        visitor_name="Recent Guest",
        guard_id=guard.id,
        authorized_by_id=owner.id,
        entered_at=datetime.now(UTC),
    )
    db_session.add_all([old, recent])
    await db_session.flush()

    purged = await service.purge_old_visits(db_session, settings)

    assert purged == 1
    remaining = list(await db_session.scalars(select(VisitLog.visitor_name)))
    assert remaining == ["Recent Guest"]
