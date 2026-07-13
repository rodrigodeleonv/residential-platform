from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.config import SettingsDep
from app.db import DbSession
from app.modules.auth.deps import AdminUser
from app.modules.billing import service
from app.modules.billing.models import Charge, ChargeKind, InfractionType
from app.modules.billing.schemas import (
    ChargeRead,
    FineCreate,
    InfractionCreate,
    InfractionRead,
    InfractionUpdate,
    MaintenanceChargeCreate,
    StatementRead,
)
from app.modules.billing.service import ChargeStatus
from app.modules.units.deps import ManagedUnit, UnitDep

router = APIRouter(tags=["billing"])


async def get_infraction_or_404(infraction_id: int, db: DbSession) -> InfractionType:
    infraction = await db.get(InfractionType, infraction_id)
    if infraction is None:
        raise HTTPException(status_code=404, detail="Infraction type not found")
    return infraction


InfractionDep = Annotated[InfractionType, Depends(get_infraction_or_404)]


# --- infraction catalog (admin only) ---


@router.post("/infractions", status_code=201)
async def create_infraction(
    payload: InfractionCreate, admin: AdminUser, db: DbSession, settings: SettingsDep
) -> InfractionRead:
    try:
        infraction = await service.create_infraction(db, payload)
    except service.InfractionNameTaken:
        raise HTTPException(
            status_code=409, detail="Infraction name already exists"
        ) from None
    return InfractionRead.of(infraction, settings.currency)


@router.get("/infractions")
async def list_infractions(
    admin: AdminUser, db: DbSession, settings: SettingsDep
) -> list[InfractionRead]:
    infractions = await service.list_infractions(db)
    return [InfractionRead.of(i, settings.currency) for i in infractions]


@router.patch("/infractions/{infraction_id}")
async def update_infraction(
    payload: InfractionUpdate,
    infraction: InfractionDep,
    admin: AdminUser,
    db: DbSession,
    settings: SettingsDep,
) -> InfractionRead:
    try:
        infraction = await service.update_infraction(db, infraction, payload)
    except service.InfractionNameTaken:
        raise HTTPException(
            status_code=409, detail="Infraction name already exists"
        ) from None
    return InfractionRead.of(infraction, settings.currency)


# --- charges (admin issues; owners read their unit's statement) ---


@router.post("/units/{unit_id}/charges", status_code=201)
async def create_maintenance_charge(
    payload: MaintenanceChargeCreate,
    unit: UnitDep,
    admin: AdminUser,
    db: DbSession,
    settings: SettingsDep,
) -> ChargeRead:
    charge = await service.create_maintenance_charge(db, unit, payload)
    return ChargeRead.of(charge, settings.currency)


@router.post("/units/{unit_id}/fines", status_code=201)
async def issue_fine(
    payload: FineCreate,
    unit: UnitDep,
    admin: AdminUser,
    db: DbSession,
    settings: SettingsDep,
) -> ChargeRead:
    infraction = await db.get(InfractionType, payload.infraction_type_id)
    if infraction is None:
        raise HTTPException(status_code=404, detail="Infraction type not found")
    try:
        charge = await service.issue_fine(db, unit, infraction)
    except service.InfractionInactive:
        raise HTTPException(
            status_code=409, detail="Infraction type is inactive"
        ) from None
    return ChargeRead.of(charge, settings.currency)


@router.get("/units/{unit_id}/statement")
async def unit_statement(
    unit: ManagedUnit, db: DbSession, settings: SettingsDep
) -> StatementRead:
    """Pending debts and paid history; only the unit's owners (or admins) see it."""
    charges = await service.unit_charges(db, unit)
    pending = [c for c in charges if c.paid_at is None]
    paid = [c for c in charges if c.paid_at is not None]
    return StatementRead(
        currency=settings.currency,
        pending=[ChargeRead.of(c, settings.currency) for c in pending],
        pending_total=sum((c.amount for c in pending), Decimal(0)),
        paid=[ChargeRead.of(c, settings.currency) for c in paid],
    )


# --- admin overview & manual payment ---


@router.get("/charges")
async def list_charges(
    admin: AdminUser,
    db: DbSession,
    settings: SettingsDep,
    unit_id: int | None = None,
    kind: ChargeKind | None = None,
    status: ChargeStatus | None = None,
) -> list[ChargeRead]:
    charges = await service.all_charges(db, unit_id=unit_id, kind=kind, status=status)
    return [ChargeRead.of(c, settings.currency) for c in charges]


@router.post("/charges/{charge_id}/pay")
async def mark_charge_paid(
    charge_id: int, admin: AdminUser, db: DbSession, settings: SettingsDep
) -> ChargeRead:
    charge = await db.get(Charge, charge_id)
    if charge is None:
        raise HTTPException(status_code=404, detail="Charge not found")
    try:
        charge = await service.mark_paid(db, charge)
    except service.ChargeVoided:
        raise HTTPException(status_code=409, detail="Charge is voided") from None
    except service.ChargeAlreadyPaid:
        raise HTTPException(status_code=409, detail="Charge is already paid") from None
    return ChargeRead.of(charge, settings.currency)
