from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.models import Charge, ChargeKind, InfractionType
from app.modules.billing.schemas import (
    InfractionCreate,
    InfractionUpdate,
    MaintenanceChargeCreate,
)
from app.modules.reservations.models import ReservableArea, Reservation
from app.modules.units.models import Unit

type ChargeStatus = Literal["pending", "paid", "voided"]


class InfractionNameTaken(Exception):
    pass


class InfractionInactive(Exception):
    pass


class ChargeAlreadyPaid(Exception):
    pass


class ChargeVoided(Exception):
    pass


# --- infraction catalog ---


async def create_infraction(db: AsyncSession, data: InfractionCreate) -> InfractionType:
    if (
        await db.scalar(
            select(InfractionType.id).where(InfractionType.name == data.name)
        )
        is not None
    ):
        raise InfractionNameTaken(data.name)
    infraction = InfractionType(**data.model_dump())
    db.add(infraction)
    await db.flush()
    return infraction


async def update_infraction(
    db: AsyncSession, infraction: InfractionType, data: InfractionUpdate
) -> InfractionType:
    changes = data.model_dump(exclude_unset=True)
    new_name = changes.get("name")
    if (
        new_name is not None
        and new_name != infraction.name
        and await db.scalar(
            select(InfractionType.id).where(InfractionType.name == new_name)
        )
        is not None
    ):
        raise InfractionNameTaken(new_name)
    for field, value in changes.items():
        setattr(infraction, field, value)
    await db.flush()
    return infraction


async def list_infractions(db: AsyncSession) -> list[InfractionType]:
    return list(await db.scalars(select(InfractionType).order_by(InfractionType.name)))


# --- charges ---


async def create_maintenance_charge(
    db: AsyncSession, unit: Unit, data: MaintenanceChargeCreate
) -> Charge:
    charge = Charge(unit_id=unit.id, kind=ChargeKind.MAINTENANCE, **data.model_dump())
    db.add(charge)
    await db.flush()
    return charge


async def issue_fine(
    db: AsyncSession, unit: Unit, infraction: InfractionType
) -> Charge:
    """Fine a unit from the catalog; name and amount are snapshotted at issue time."""
    if not infraction.is_active:
        raise InfractionInactive
    charge = Charge(
        unit_id=unit.id,
        kind=ChargeKind.FINE,
        description=infraction.name,
        amount=infraction.fine_amount,
        infraction_type_id=infraction.id,
    )
    db.add(charge)
    await db.flush()
    return charge


async def create_reservation_charge(
    db: AsyncSession, reservation: Reservation, area: ReservableArea
) -> Charge | None:
    """Bill the slot fee at booking time; free areas produce no charge."""
    if reservation.fee <= 0:
        return None
    charge = Charge(
        unit_id=reservation.unit_id,
        kind=ChargeKind.RESERVATION,
        description=f"{area.name} — {reservation.day} ({reservation.slot})",
        amount=reservation.fee,
        reservation_id=reservation.id,
    )
    db.add(charge)
    await db.flush()
    return charge


async def void_reservation_charge(db: AsyncSession, reservation: Reservation) -> None:
    """Void the pending charge of a canceled reservation; a paid charge is kept."""
    charge = await db.scalar(
        select(Charge).where(
            Charge.reservation_id == reservation.id,
            Charge.paid_at.is_(None),
            Charge.voided_at.is_(None),
        )
    )
    if charge is not None:
        charge.voided_at = datetime.now(UTC)
        await db.flush()


async def unit_charges(db: AsyncSession, unit: Unit) -> list[Charge]:
    """The unit's statement lines: every non-voided charge, oldest first."""
    return list(
        await db.scalars(
            select(Charge)
            .where(Charge.unit_id == unit.id, Charge.voided_at.is_(None))
            .order_by(Charge.id)
        )
    )


async def all_charges(
    db: AsyncSession,
    *,
    unit_id: int | None = None,
    kind: ChargeKind | None = None,
    status: ChargeStatus | None = None,
) -> list[Charge]:
    query = select(Charge).order_by(Charge.id)
    if unit_id is not None:
        query = query.where(Charge.unit_id == unit_id)
    if kind is not None:
        query = query.where(Charge.kind == kind)
    match status:
        case "pending":
            query = query.where(Charge.paid_at.is_(None), Charge.voided_at.is_(None))
        case "paid":
            query = query.where(Charge.paid_at.is_not(None))
        case "voided":
            query = query.where(Charge.voided_at.is_not(None))
    return list(await db.scalars(query))


async def mark_paid(db: AsyncSession, charge: Charge) -> Charge:
    if charge.voided_at is not None:
        raise ChargeVoided
    if charge.paid_at is not None:
        raise ChargeAlreadyPaid
    charge.paid_at = datetime.now(UTC)
    await db.flush()
    return charge
