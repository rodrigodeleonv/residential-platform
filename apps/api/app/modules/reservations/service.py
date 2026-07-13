from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.billing import service as billing_service
from app.modules.reservations.models import ReservableArea, Reservation, TimeSlot
from app.modules.reservations.schemas import AreaCreate, AreaUpdate, ReservationCreate
from app.modules.units.models import Unit
from app.modules.users.models import User


class AreaNameTaken(Exception):
    pass


class AreaInactive(Exception):
    pass


class SlotEnded(Exception):
    pass


class SlotFull(Exception):
    pass


class DuplicateReservation(Exception):
    pass


class CancelWindowClosed(Exception):
    pass


SLOT_START_HOUR: dict[TimeSlot, int] = {
    TimeSlot.MORNING: 6,
    TimeSlot.AFTERNOON: 12,
    TimeSlot.EVENING: 18,
}
SLOT_LENGTH = timedelta(hours=6)


def slot_bounds(
    day: date, slot: TimeSlot, settings: Settings
) -> tuple[datetime, datetime]:
    """Start and end of a slot as aware datetimes in the condominium's timezone."""
    tz = ZoneInfo(settings.local_timezone)
    start = datetime.combine(day, time(SLOT_START_HOUR[slot]), tzinfo=tz)
    return start, start + SLOT_LENGTH


def _active_slot_clause(area_id: int, day: date, slot: TimeSlot) -> ColumnElement[bool]:
    return and_(
        Reservation.area_id == area_id,
        Reservation.day == day,
        Reservation.slot == slot,
        Reservation.canceled_at.is_(None),
    )


# --- area catalog ---


async def create_area(db: AsyncSession, data: AreaCreate) -> ReservableArea:
    if (
        await db.scalar(
            select(ReservableArea.id).where(ReservableArea.name == data.name)
        )
        is not None
    ):
        raise AreaNameTaken(data.name)
    area = ReservableArea(**data.model_dump())
    db.add(area)
    await db.flush()
    return area


async def update_area(
    db: AsyncSession, area: ReservableArea, data: AreaUpdate
) -> ReservableArea:
    changes = data.model_dump(exclude_unset=True)
    new_name = changes.get("name")
    if (
        new_name is not None
        and new_name != area.name
        and await db.scalar(
            select(ReservableArea.id).where(ReservableArea.name == new_name)
        )
        is not None
    ):
        raise AreaNameTaken(new_name)
    for field, value in changes.items():
        setattr(area, field, value)
    await db.flush()
    return area


async def list_areas(
    db: AsyncSession, *, include_inactive: bool = False
) -> list[ReservableArea]:
    query = select(ReservableArea).order_by(ReservableArea.name)
    if not include_inactive:
        query = query.where(ReservableArea.is_active)
    return list(await db.scalars(query))


async def booked_counts(
    db: AsyncSession, area: ReservableArea, day: date
) -> dict[TimeSlot, int]:
    """Active reservations per slot for one area and day (every slot present)."""
    rows = await db.execute(
        select(Reservation.slot, func.count())
        .where(
            Reservation.area_id == area.id,
            Reservation.day == day,
            Reservation.canceled_at.is_(None),
        )
        .group_by(Reservation.slot)
    )
    return dict.fromkeys(TimeSlot, 0) | dict(rows.tuples().all())


# --- reservations ---


async def create_reservation(
    db: AsyncSession,
    area: ReservableArea,
    unit: Unit,
    user: User,
    data: ReservationCreate,
    settings: Settings,
) -> Reservation:
    if not area.is_active:
        raise AreaInactive
    _, slot_end = slot_bounds(data.day, data.slot, settings)
    if datetime.now(UTC) >= slot_end:
        raise SlotEnded
    active_slot = _active_slot_clause(area.id, data.day, data.slot)
    if (
        await db.scalar(
            select(Reservation.id).where(active_slot, Reservation.user_id == user.id)
        )
        is not None
    ):
        raise DuplicateReservation
    booked = await db.scalar(
        select(func.count()).select_from(Reservation).where(active_slot)
    )
    if booked is not None and booked >= area.capacity:
        raise SlotFull
    reservation = Reservation(
        area_id=area.id,
        unit_id=unit.id,
        user_id=user.id,
        day=data.day,
        slot=data.slot,
        fee=area.fee,
    )
    db.add(reservation)
    await db.flush()
    await billing_service.create_reservation_charge(db, reservation, area)
    return reservation


async def unit_reservations(db: AsyncSession, unit: Unit) -> list[Reservation]:
    return list(
        await db.scalars(
            select(Reservation)
            .where(Reservation.unit_id == unit.id)
            .order_by(Reservation.day, Reservation.id)
        )
    )


async def all_reservations(
    db: AsyncSession, *, day: date | None = None, area_id: int | None = None
) -> list[Reservation]:
    query = select(Reservation).order_by(Reservation.day, Reservation.id)
    if day is not None:
        query = query.where(Reservation.day == day)
    if area_id is not None:
        query = query.where(Reservation.area_id == area_id)
    return list(await db.scalars(query))


async def cancel_reservation(
    db: AsyncSession, reservation: Reservation, *, override: bool, settings: Settings
) -> None:
    """Cancel before the slot starts; admins (override) may cancel anytime."""
    slot_start, _ = slot_bounds(reservation.day, reservation.slot, settings)
    if not override and datetime.now(UTC) >= slot_start:
        raise CancelWindowClosed
    reservation.canceled_at = datetime.now(UTC)
    await db.flush()
    await billing_service.void_reservation_charge(db, reservation)
