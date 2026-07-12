from datetime import UTC, date, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.audit.models import AuditLog
from app.modules.users.models import Role
from tests.conftest import LoginAs, RoleGranter, UnitFactory, UserFactory
from tests.utils import API

TODAY = date.today()
ACTIVE = {"starts_on": TODAY, "ends_on": TODAY + timedelta(days=365)}


def one_off(
    settings: Settings, *, hours_from_now: int = 1, **overrides: object
) -> dict[str, object]:
    return {
        "visitor_name": "Visiting Friend",
        "kind": "one_off",
        "expiration_hours": settings.visit_expiration_hours_options[0],
        "starts_at": (datetime.now(UTC) + timedelta(hours=hours_from_now)).isoformat(),
        **overrides,
    }


def recurring(settings: Settings, **overrides: object) -> dict[str, object]:
    return {
        "visitor_name": "Weekly Cleaner",
        "kind": "recurring",
        "expiration_hours": settings.visit_expiration_hours_options[0],
        "weekday": 0,
        "time_of_day": "09:00:00",
        "valid_from": str(TODAY),
        "valid_until": str(TODAY + timedelta(days=60)),
        **overrides,
    }


async def test_resident_creates_one_off_preregistration(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
    settings: Settings,
    db_session: AsyncSession,
) -> None:
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await login_as(owner)

    response = await client.post(
        f"{API}/units/{unit.id}/preregistrations",
        json=one_off(settings, visitor_plate="vis 001"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["visitor_plate"] == "VIS001"
    entry = await db_session.scalar(
        select(AuditLog).where(AuditLog.event == "preregistration_created")
    )
    assert entry is not None
    assert entry.actor_id == owner.id


async def test_non_resident_owner_cannot_preregister(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
    settings: Settings,
) -> None:
    owner = await create_user("owner@example.com")
    tenant = await create_user("tenant@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await grant_role(tenant, Role.TENANT, unit, **ACTIVE)
    await login_as(owner)

    response = await client.post(
        f"{API}/units/{unit.id}/preregistrations", json=one_off(settings)
    )

    assert response.status_code == 403


async def test_expiration_must_be_an_allowed_option(
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
    bad_hours = max(settings.visit_expiration_hours_options) + 1

    response = await client.post(
        f"{API}/units/{unit.id}/preregistrations",
        json=one_off(settings, expiration_hours=bad_hours),
    )

    assert response.status_code == 422


async def test_advance_limit_is_enforced(
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
    too_far = datetime.now(UTC) + timedelta(days=settings.visit_max_advance_days + 2)

    response = await client.post(
        f"{API}/units/{unit.id}/preregistrations",
        json=one_off(settings, starts_at=too_far.isoformat()),
    )

    assert response.status_code == 422


async def test_recurring_range_limit_is_enforced(
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
    too_long = TODAY + timedelta(days=settings.visit_recurring_max_days + 2)

    response = await client.post(
        f"{API}/units/{unit.id}/preregistrations",
        json=recurring(settings, valid_until=str(too_long)),
    )

    assert response.status_code == 422


async def test_kind_shape_is_validated(
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

    # a recurring pre-registration missing its fields
    response = await client.post(
        f"{API}/units/{unit.id}/preregistrations",
        json={
            "visitor_name": "X",
            "kind": "recurring",
            "expiration_hours": settings.visit_expiration_hours_options[0],
        },
    )

    assert response.status_code == 422


async def test_update_and_cancel_are_audited(
    client: AsyncClient,
    create_user: UserFactory,
    create_unit: UnitFactory,
    login_as: LoginAs,
    grant_role: RoleGranter,
    settings: Settings,
    db_session: AsyncSession,
) -> None:
    owner = await create_user("owner@example.com")
    unit = await create_unit("H-1")
    await grant_role(owner, Role.OWNER, unit)
    await login_as(owner)
    prereg = (
        await client.post(
            f"{API}/units/{unit.id}/preregistrations", json=one_off(settings)
        )
    ).json()

    updated = await client.patch(
        f"{API}/units/{unit.id}/preregistrations/{prereg['id']}",
        json={"visitor_name": "Renamed Guest"},
    )
    assert updated.status_code == 200
    assert updated.json()["visitor_name"] == "Renamed Guest"

    assert (
        await client.delete(f"{API}/units/{unit.id}/preregistrations/{prereg['id']}")
    ).status_code == 204
    assert (await client.get(f"{API}/units/{unit.id}/preregistrations")).json() == []

    events = [
        e
        async for e in await db_session.stream_scalars(
            select(AuditLog.event).where(AuditLog.event.like("preregistration_%"))
        )
    ]
    assert events == [
        "preregistration_created",
        "preregistration_updated",
        "preregistration_canceled",
    ]


async def test_update_cannot_break_policy(
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
    prereg = (
        await client.post(
            f"{API}/units/{unit.id}/preregistrations", json=one_off(settings)
        )
    ).json()

    response = await client.patch(
        f"{API}/units/{unit.id}/preregistrations/{prereg['id']}",
        json={"expiration_hours": max(settings.visit_expiration_hours_options) + 1},
    )

    assert response.status_code == 422
