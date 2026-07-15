from fastapi import APIRouter, HTTPException

from app.config import SettingsDep
from app.db import DbSession
from app.email import EmailDep
from app.modules.auth.deps import AdminUser, CurrentUser, GuardUser
from app.modules.units import service
from app.modules.units.deps import ManagedUnit, UnitDep
from app.modules.units.schemas import (
    BuildingCreate,
    BuildingRead,
    OwnerAssign,
    TenancyRead,
    TenancyUpdate,
    TenantRegister,
    UnitCreate,
    UnitRead,
    VisitorParkingSpotCreate,
    VisitorParkingSpotRead,
)
from app.modules.users.models import User
from app.modules.users.schemas import UserRead

router = APIRouter(tags=["units"])


# --- physical structure (admin) ---


@router.post("/buildings", status_code=201)
async def create_building(
    payload: BuildingCreate, admin: AdminUser, db: DbSession
) -> BuildingRead:
    try:
        building = await service.create_building(db, payload.name)
    except service.NameTaken:
        raise HTTPException(
            status_code=409, detail="Building name already exists"
        ) from None
    return BuildingRead.model_validate(building)


@router.get("/buildings")
async def list_buildings(admin: AdminUser, db: DbSession) -> list[BuildingRead]:
    return [BuildingRead.model_validate(b) for b in await service.list_buildings(db)]


@router.post("/units", status_code=201)
async def create_unit(payload: UnitCreate, admin: AdminUser, db: DbSession) -> UnitRead:
    try:
        unit = await service.create_unit(db, payload)
    except service.BuildingNotFound:
        raise HTTPException(status_code=404, detail="Building not found") from None
    except service.NameTaken:
        raise HTTPException(
            status_code=409, detail="Unit number already exists in that location"
        ) from None
    return UnitRead.model_validate(unit)


@router.get("/units")
async def list_units(admin: AdminUser, db: DbSession) -> list[UnitRead]:
    return [UnitRead.model_validate(u) for u in await service.list_units(db)]


@router.get("/units/mine")
async def my_units(user: CurrentUser, db: DbSession) -> list[UnitRead]:
    """Units the current user owns or actively rents."""
    return [UnitRead.model_validate(u) for u in await service.units_of(db, user.id)]


@router.post("/visitor-parking-spots", status_code=201)
async def create_visitor_spot(
    payload: VisitorParkingSpotCreate, admin: AdminUser, db: DbSession
) -> VisitorParkingSpotRead:
    try:
        spot = await service.create_visitor_spot(db, payload.number)
    except service.NameTaken:
        raise HTTPException(
            status_code=409, detail="Spot number already exists"
        ) from None
    return VisitorParkingSpotRead.model_validate(spot)


@router.get("/visitor-parking-spots")
async def list_visitor_spots(
    guard: GuardUser, db: DbSession
) -> list[VisitorParkingSpotRead]:
    """Guards also read this list: they assign a spot when registering an entry."""
    return [
        VisitorParkingSpotRead.model_validate(s)
        for s in await service.list_visitor_spots(db)
    ]


# --- ownership (admin) ---


@router.post("/units/{unit_id}/owners", status_code=201)
async def assign_owner(
    payload: OwnerAssign, unit: UnitDep, admin: AdminUser, db: DbSession
) -> UserRead:
    user = await db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        await service.assign_owner(db, unit, user, actor=admin)
    except service.AlreadyAssigned:
        raise HTTPException(
            status_code=409, detail="Already an owner of this unit"
        ) from None
    return UserRead.model_validate(user)


@router.get("/units/{unit_id}/owners")
async def list_owners(unit: ManagedUnit, db: DbSession) -> list[UserRead]:
    return [UserRead.model_validate(u) for u in await service.owners_of(db, unit)]


@router.delete("/units/{unit_id}/owners/{user_id}", status_code=204)
async def remove_owner(
    unit: UnitDep, user_id: int, admin: AdminUser, db: DbSession
) -> None:
    if not await service.remove_owner(db, unit, user_id, actor=admin):
        raise HTTPException(status_code=404, detail="Not an owner of this unit")


# --- tenancy (unit owners or admin) ---


@router.post("/units/{unit_id}/tenants", status_code=201)
async def register_tenant(
    payload: TenantRegister,
    unit: ManagedUnit,
    user: CurrentUser,
    db: DbSession,
    provider: EmailDep,
    settings: SettingsDep,
) -> TenancyRead:
    try:
        tenancy = await service.register_tenant(
            db, unit, payload, actor=user, provider=provider, settings=settings
        )
    except service.AlreadyAssigned:
        raise HTTPException(
            status_code=409, detail="Already a tenant of this unit"
        ) from None
    return TenancyRead.model_validate(tenancy)


@router.get("/units/{unit_id}/tenants")
async def list_tenants(unit: ManagedUnit, db: DbSession) -> list[TenancyRead]:
    return [
        TenancyRead.model_validate(t) for t in await service.list_tenancies(db, unit)
    ]


@router.patch("/units/{unit_id}/tenants/{tenancy_id}")
async def update_tenancy(
    payload: TenancyUpdate,
    unit: ManagedUnit,
    tenancy_id: int,
    user: CurrentUser,
    db: DbSession,
) -> TenancyRead:
    tenancy = await service.get_tenancy(db, unit.id, tenancy_id)
    if tenancy is None:
        raise HTTPException(status_code=404, detail="Tenancy not found")
    try:
        tenancy = await service.update_tenancy(db, tenancy, payload, actor=user)
    except service.InvalidTenancyRange:
        raise HTTPException(
            status_code=422, detail="ends_on must be on or after starts_on"
        ) from None
    return TenancyRead.model_validate(tenancy)


@router.delete("/units/{unit_id}/tenants/{tenancy_id}", status_code=204)
async def revoke_tenancy(
    unit: ManagedUnit, tenancy_id: int, user: CurrentUser, db: DbSession
) -> None:
    tenancy = await service.get_tenancy(db, unit.id, tenancy_id)
    if tenancy is None:
        raise HTTPException(status_code=404, detail="Tenancy not found")
    await service.revoke_tenancy(db, tenancy, actor=user)
