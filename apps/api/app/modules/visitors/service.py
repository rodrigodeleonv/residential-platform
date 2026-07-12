from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.audit import service as audit
from app.modules.units import service as units
from app.modules.units.models import Unit, VisitorParkingSpot
from app.modules.users.models import User
from app.modules.vehicles import service as vehicles
from app.modules.visitors.models import PreRegKind, VisitLog, VisitPreRegistration
from app.modules.visitors.schemas import (
    GatehouseResident,
    GatehouseUnitCard,
    PreRegistrationCreate,
    PreRegistrationUpdate,
    VisitEntryCreate,
)


class InvalidPolicy(Exception):
    """The pre-registration violates a deployment policy (expiration, advance, range)."""


class InvalidAuthorization(Exception):
    """The entry's authorization is not valid (not a resident / no active pre-registration)."""


class SpotUnavailable(Exception):
    pass


class AlreadyExited(Exception):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


# --- pre-registrations (resident side) ---


def _validate_policy(
    data: PreRegistrationCreate, settings: Settings, now: datetime
) -> None:
    if data.expiration_hours not in settings.visit_expiration_hours_options:
        raise InvalidPolicy(
            f"expiration_hours must be one of {sorted(settings.visit_expiration_hours_options)}"
        )
    horizon = now.date() + timedelta(days=settings.visit_max_advance_days)
    if data.kind is PreRegKind.ONE_OFF:
        assert data.starts_at is not None
        if data.starts_at + timedelta(hours=data.expiration_hours) <= now:
            raise InvalidPolicy("the visit window is already over")
        if data.starts_at.date() > horizon:
            raise InvalidPolicy(
                f"visits can be pre-registered at most {settings.visit_max_advance_days} days ahead"
            )
    else:
        assert data.valid_from is not None and data.valid_until is not None
        if data.valid_from > horizon:
            raise InvalidPolicy(
                f"visits can be pre-registered at most {settings.visit_max_advance_days} days ahead"
            )
        if (
            data.valid_until - data.valid_from
        ).days > settings.visit_recurring_max_days:
            raise InvalidPolicy(
                f"a recurring range spans at most {settings.visit_recurring_max_days} days"
            )


async def create_preregistration(
    db: AsyncSession,
    unit: Unit,
    data: PreRegistrationCreate,
    actor: User,
    settings: Settings,
) -> VisitPreRegistration:
    _validate_policy(data, settings, _now())
    prereg = VisitPreRegistration(
        unit_id=unit.id,
        created_by_id=actor.id,
        visitor_name=data.visitor_name,
        visitor_plate=data.visitor_plate,
        kind=data.kind,
        expiration_hours=data.expiration_hours,
        starts_at=data.starts_at,
        weekday=data.weekday,
        time_of_day=data.time_of_day,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
    )
    db.add(prereg)
    await db.flush()
    await audit.record(
        db,
        "preregistration_created",
        actor_id=actor.id,
        data={"unit_id": unit.id, "preregistration_id": prereg.id, "kind": data.kind},
    )
    return prereg


async def update_preregistration(
    db: AsyncSession,
    prereg: VisitPreRegistration,
    data: PreRegistrationUpdate,
    actor: User,
    settings: Settings,
) -> VisitPreRegistration:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(prereg, field, value)
    merged = PreRegistrationCreate.model_validate(prereg, from_attributes=True)
    _validate_policy(merged, settings, _now())
    await db.flush()
    await audit.record(
        db,
        "preregistration_updated",
        actor_id=actor.id,
        data={"unit_id": prereg.unit_id, "preregistration_id": prereg.id},
    )
    return prereg


async def cancel_preregistration(
    db: AsyncSession, prereg: VisitPreRegistration, actor: User
) -> None:
    await audit.record(
        db,
        "preregistration_canceled",
        actor_id=actor.id,
        data={"unit_id": prereg.unit_id, "preregistration_id": prereg.id},
    )
    await db.delete(prereg)


async def list_preregistrations(
    db: AsyncSession, unit: Unit
) -> list[VisitPreRegistration]:
    return list(
        await db.scalars(
            select(VisitPreRegistration)
            .where(VisitPreRegistration.unit_id == unit.id)
            .order_by(VisitPreRegistration.id)
        )
    )


async def get_preregistration(
    db: AsyncSession, unit_id: int, prereg_id: int
) -> VisitPreRegistration | None:
    return await db.scalar(
        select(VisitPreRegistration).where(
            VisitPreRegistration.id == prereg_id,
            VisitPreRegistration.unit_id == unit_id,
        )
    )


# --- active-window evaluation ---


def is_active_at(
    prereg: VisitPreRegistration, at: datetime, settings: Settings
) -> bool:
    """True when the guard should see this pre-registration and let the visitor in."""
    window = timedelta(hours=prereg.expiration_hours)
    if prereg.kind is PreRegKind.ONE_OFF:
        assert prereg.starts_at is not None
        return prereg.starts_at <= at < prereg.starts_at + window

    assert (
        prereg.weekday is not None
        and prereg.time_of_day is not None
        and prereg.valid_from is not None
        and prereg.valid_until is not None
    )
    tz = ZoneInfo(settings.local_timezone)
    local = at.astimezone(tz)
    # A window opened today or yesterday may still be running (it can cross midnight).
    for days_back in (0, 1):
        candidate = local.date() - timedelta(days=days_back)
        if candidate.weekday() != prereg.weekday:
            continue
        if not (prereg.valid_from <= candidate <= prereg.valid_until):
            continue
        opens = datetime.combine(candidate, prereg.time_of_day, tz)
        if opens <= at < opens + window:
            return True
    return False


async def active_preregistrations(
    db: AsyncSession, unit: Unit, settings: Settings, at: datetime | None = None
) -> list[VisitPreRegistration]:
    at = at or _now()
    return [
        prereg
        for prereg in await list_preregistrations(db, unit)
        if is_active_at(prereg, at, settings)
    ]


# --- gatehouse ---


async def unit_card(db: AsyncSession, unit: Unit) -> GatehouseUnitCard:
    """The restricted subset of unit data a guard may see."""
    residents = await units.residents_of(db, unit)
    return GatehouseUnitCard(
        unit_id=unit.id,
        kind=unit.kind,
        number=unit.number,
        building_name=unit.building.name if unit.building else None,
        residents=[
            GatehouseResident(full_name=r.full_name, phone=r.phone) for r in residents
        ],
        plates=[v.plate for v in await vehicles.list_vehicles(db, unit)],
        parking_spot_numbers=[
            s.number for s in await vehicles.list_parking_spots(db, unit)
        ],
    )


async def register_entry(
    db: AsyncSession,
    unit: Unit,
    data: VisitEntryCreate,
    guard: User,
    settings: Settings,
) -> VisitLog:
    authorized_by_id: int | None = None
    preregistration_id: int | None = None

    if data.authorized_by_user_id is not None:  # flow A: live approval over the phone
        if not await units.is_resident(db, data.authorized_by_user_id, unit.id):
            raise InvalidAuthorization(
                "the authorizing user does not reside in this unit"
            )
        authorized_by_id = data.authorized_by_user_id
    else:  # flow B: pre-registration, valid right now
        assert data.preregistration_id is not None
        prereg = await get_preregistration(db, unit.id, data.preregistration_id)
        if prereg is None or not is_active_at(prereg, _now(), settings):
            raise InvalidAuthorization("no valid pre-registration for this visit")
        preregistration_id = prereg.id

    if data.visitor_spot_id is not None:
        spot = await db.get(VisitorParkingSpot, data.visitor_spot_id)
        if spot is None:
            raise SpotUnavailable("visitor parking spot not found")
        occupied = await db.scalar(
            select(VisitLog.id).where(
                VisitLog.visitor_spot_id == spot.id, VisitLog.exited_at.is_(None)
            )
        )
        if occupied is not None:
            raise SpotUnavailable("visitor parking spot is occupied")

    visit = VisitLog(
        unit_id=unit.id,
        visitor_name=data.visitor_name,
        visitor_plate=data.visitor_plate,
        visitor_spot_id=data.visitor_spot_id,
        guard_id=guard.id,
        authorized_by_id=authorized_by_id,
        preregistration_id=preregistration_id,
        entered_at=_now(),
    )
    db.add(visit)
    await db.flush()
    await audit.record(
        db,
        "visitor_entry",
        actor_id=guard.id,
        target_user_id=authorized_by_id,
        data={
            "unit_id": unit.id,
            "visit_id": visit.id,
            "visitor_name": data.visitor_name,
            "authorized_by_id": authorized_by_id,
            "preregistration_id": preregistration_id,
        },
    )
    return visit


async def register_exit(db: AsyncSession, visit: VisitLog) -> VisitLog:
    if visit.exited_at is not None:
        raise AlreadyExited
    visit.exited_at = _now()
    await db.flush()
    return visit


async def list_visits(db: AsyncSession, *, open_only: bool = False) -> list[VisitLog]:
    stmt = select(VisitLog).order_by(VisitLog.id)
    if open_only:
        stmt = stmt.where(VisitLog.exited_at.is_(None))
    return list(await db.scalars(stmt))


async def purge_old_visits(db: AsyncSession, settings: Settings) -> int:
    """Retention cleanup; meant to be run periodically (cron) or manually."""
    cutoff = _now() - timedelta(days=settings.visit_log_retention_days)
    old_ids = list(
        await db.scalars(select(VisitLog.id).where(VisitLog.entered_at < cutoff))
    )
    if old_ids:
        await db.execute(delete(VisitLog).where(VisitLog.id.in_(old_ids)))
    return len(old_ids)
