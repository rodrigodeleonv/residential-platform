from fastapi import APIRouter, HTTPException

from app.config import SettingsDep
from app.db import DbSession
from app.modules.auth.deps import CurrentUser, GuardUser
from app.modules.units.deps import ResidentUnit, UnitDep
from app.modules.units.models import Unit
from app.modules.visitors import service
from app.modules.visitors.models import VisitLog, VisitPreRegistration
from app.modules.visitors.schemas import (
    GatehouseUnitCard,
    PreRegistrationCreate,
    PreRegistrationRead,
    PreRegistrationUpdate,
    VisitEntryCreate,
    VisitRead,
)

router = APIRouter(tags=["visitors"])


# --- pre-registrations (residents of the unit) ---


async def _prereg_or_404(
    db: DbSession, unit_id: int, prereg_id: int
) -> VisitPreRegistration:
    prereg = await service.get_preregistration(db, unit_id, prereg_id)
    if prereg is None:
        raise HTTPException(status_code=404, detail="Pre-registration not found")
    return prereg


@router.post("/units/{unit_id}/preregistrations", status_code=201)
async def create_preregistration(
    payload: PreRegistrationCreate,
    unit: ResidentUnit,
    user: CurrentUser,
    db: DbSession,
    settings: SettingsDep,
) -> PreRegistrationRead:
    try:
        prereg = await service.create_preregistration(db, unit, payload, user, settings)
    except service.InvalidPolicy as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return PreRegistrationRead.model_validate(prereg)


@router.get("/units/{unit_id}/preregistrations")
async def list_preregistrations(
    unit: ResidentUnit, db: DbSession
) -> list[PreRegistrationRead]:
    preregs = await service.list_preregistrations(db, unit)
    return [PreRegistrationRead.model_validate(p) for p in preregs]


@router.patch("/units/{unit_id}/preregistrations/{prereg_id}")
async def update_preregistration(
    payload: PreRegistrationUpdate,
    unit: ResidentUnit,
    prereg_id: int,
    user: CurrentUser,
    db: DbSession,
    settings: SettingsDep,
) -> PreRegistrationRead:
    prereg = await _prereg_or_404(db, unit.id, prereg_id)
    try:
        prereg = await service.update_preregistration(
            db, prereg, payload, user, settings
        )
    except service.InvalidPolicy as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return PreRegistrationRead.model_validate(prereg)


@router.delete("/units/{unit_id}/preregistrations/{prereg_id}", status_code=204)
async def cancel_preregistration(
    unit: ResidentUnit, prereg_id: int, user: CurrentUser, db: DbSession
) -> None:
    prereg = await _prereg_or_404(db, unit.id, prereg_id)
    await service.cancel_preregistration(db, prereg, user)


# --- gatehouse (guards and admins) ---


@router.get("/gatehouse/units/{unit_id}")
async def gatehouse_unit_card(
    unit: UnitDep, guard: GuardUser, db: DbSession
) -> GatehouseUnitCard:
    return await service.unit_card(db, unit)


@router.get("/gatehouse/units/{unit_id}/active-preregistrations")
async def gatehouse_active_preregistrations(
    unit: UnitDep, guard: GuardUser, db: DbSession, settings: SettingsDep
) -> list[PreRegistrationRead]:
    active = await service.active_preregistrations(db, unit, settings)
    return [PreRegistrationRead.model_validate(p) for p in active]


@router.post("/gatehouse/visits", status_code=201)
async def register_entry(
    payload: VisitEntryCreate, guard: GuardUser, db: DbSession, settings: SettingsDep
) -> VisitRead:
    unit = await db.get(Unit, payload.unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    try:
        visit = await service.register_entry(db, unit, payload, guard, settings)
    except service.InvalidAuthorization as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except service.SpotUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return VisitRead.model_validate(visit)


@router.post("/gatehouse/visits/{visit_id}/exit")
async def register_exit(visit_id: int, guard: GuardUser, db: DbSession) -> VisitRead:
    visit = await db.get(VisitLog, visit_id)
    if visit is None:
        raise HTTPException(status_code=404, detail="Visit not found")
    try:
        visit = await service.register_exit(db, visit)
    except service.AlreadyExited:
        raise HTTPException(status_code=409, detail="Exit already recorded") from None
    return VisitRead.model_validate(visit)


@router.get("/gatehouse/visits")
async def list_visits(
    guard: GuardUser, db: DbSession, open_only: bool = False
) -> list[VisitRead]:
    return [
        VisitRead.model_validate(v)
        for v in await service.list_visits(db, open_only=open_only)
    ]
