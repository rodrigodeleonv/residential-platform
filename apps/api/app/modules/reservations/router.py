from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.config import SettingsDep
from app.db import DbSession
from app.modules.auth.deps import AdminUser, CurrentUser
from app.modules.reservations import service
from app.modules.reservations.models import ReservableArea, Reservation
from app.modules.reservations.schemas import (
    AreaCreate,
    AreaRead,
    AreaUpdate,
    ReservationCreate,
    ReservationRead,
    SlotAvailability,
)
from app.modules.units.deps import MemberUnit, ResidentUnit
from app.modules.users.models import Role

router = APIRouter(tags=["reservations"])


async def get_area_or_404(area_id: int, db: DbSession) -> ReservableArea:
    area = await db.get(ReservableArea, area_id)
    if area is None:
        raise HTTPException(status_code=404, detail="Area not found")
    return area


AreaDep = Annotated[ReservableArea, Depends(get_area_or_404)]


# --- area catalog (admin manages, any authenticated user consults) ---


@router.post("/areas", status_code=201)
async def create_area(
    payload: AreaCreate, admin: AdminUser, db: DbSession, settings: SettingsDep
) -> AreaRead:
    try:
        area = await service.create_area(db, payload)
    except service.AreaNameTaken:
        raise HTTPException(
            status_code=409, detail="Area name already exists"
        ) from None
    return AreaRead.of(area, settings.currency)


@router.get("/areas")
async def list_areas(
    user: CurrentUser, db: DbSession, settings: SettingsDep
) -> list[AreaRead]:
    """Active areas; admins also see inactive ones."""
    areas = await service.list_areas(db, include_inactive=Role.ADMIN in user.roles)
    return [AreaRead.of(area, settings.currency) for area in areas]


@router.patch("/areas/{area_id}")
async def update_area(
    payload: AreaUpdate,
    area: AreaDep,
    admin: AdminUser,
    db: DbSession,
    settings: SettingsDep,
) -> AreaRead:
    try:
        area = await service.update_area(db, area, payload)
    except service.AreaNameTaken:
        raise HTTPException(
            status_code=409, detail="Area name already exists"
        ) from None
    return AreaRead.of(area, settings.currency)


@router.get("/areas/{area_id}/availability")
async def area_availability(
    area: AreaDep, day: date, user: CurrentUser, db: DbSession
) -> list[SlotAvailability]:
    booked = await service.booked_counts(db, area, day)
    return [
        SlotAvailability(
            slot=slot,
            capacity=area.capacity,
            booked=count,
            available=area.capacity - count,
        )
        for slot, count in booked.items()
    ]


# --- reservations (residents book for their unit) ---


@router.post("/units/{unit_id}/reservations", status_code=201)
async def create_reservation(
    payload: ReservationCreate,
    unit: ResidentUnit,
    user: CurrentUser,
    db: DbSession,
    settings: SettingsDep,
) -> ReservationRead:
    area = await db.get(ReservableArea, payload.area_id)
    if area is None:
        raise HTTPException(status_code=404, detail="Area not found")
    try:
        reservation = await service.create_reservation(
            db, area, unit, user, payload, settings
        )
    except service.AreaInactive:
        raise HTTPException(
            status_code=409, detail="Area is not accepting reservations"
        ) from None
    except service.SlotEnded:
        raise HTTPException(
            status_code=422, detail="This time slot has already ended"
        ) from None
    except service.DuplicateReservation:
        raise HTTPException(
            status_code=409, detail="You already reserved this slot"
        ) from None
    except service.SlotFull:
        raise HTTPException(
            status_code=409, detail="No capacity left for this slot"
        ) from None
    return ReservationRead.of(reservation, settings.currency)


@router.get("/units/{unit_id}/reservations")
async def list_unit_reservations(
    unit: MemberUnit, db: DbSession, settings: SettingsDep
) -> list[ReservationRead]:
    reservations = await service.unit_reservations(db, unit)
    return [ReservationRead.of(r, settings.currency) for r in reservations]


@router.delete("/units/{unit_id}/reservations/{reservation_id}", status_code=204)
async def cancel_reservation(
    unit: ResidentUnit,
    reservation_id: int,
    user: CurrentUser,
    db: DbSession,
    settings: SettingsDep,
) -> None:
    reservation = await db.scalar(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.unit_id == unit.id,
            Reservation.canceled_at.is_(None),
        )
    )
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    is_admin = Role.ADMIN in user.roles
    if not is_admin and reservation.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the reservation creator or an admin can cancel",
        )
    try:
        await service.cancel_reservation(
            db, reservation, override=is_admin, settings=settings
        )
    except service.CancelWindowClosed:
        raise HTTPException(
            status_code=409, detail="The slot has already started"
        ) from None


# --- admin overview ---


@router.get("/reservations")
async def list_reservations(
    admin: AdminUser,
    db: DbSession,
    settings: SettingsDep,
    day: date | None = None,
    area_id: int | None = None,
) -> list[ReservationRead]:
    reservations = await service.all_reservations(db, day=day, area_id=area_id)
    return [ReservationRead.of(r, settings.currency) for r in reservations]
