from fastapi import APIRouter, HTTPException

from app.config import SettingsDep
from app.db import DbSession
from app.modules.auth.deps import AdminUser
from app.modules.units.deps import MemberUnit, ResidentUnit, UnitDep
from app.modules.vehicles import service
from app.modules.vehicles.schemas import (
    ParkingSpotCreate,
    ParkingSpotRead,
    VehicleCreate,
    VehicleRead,
)

router = APIRouter(tags=["vehicles"])


# --- assigned parking spots (admin manages, unit members view) ---


@router.post("/units/{unit_id}/parking-spots", status_code=201)
async def add_parking_spot(
    payload: ParkingSpotCreate,
    unit: UnitDep,
    admin: AdminUser,
    db: DbSession,
    settings: SettingsDep,
) -> ParkingSpotRead:
    try:
        spot = await service.add_parking_spot(db, unit, payload.number, settings)
    except service.NumberTaken:
        raise HTTPException(
            status_code=409, detail="Spot number already exists"
        ) from None
    except service.SpotLimitReached:
        raise HTTPException(
            status_code=409,
            detail="This unit already has all its assigned parking spots",
        ) from None
    return ParkingSpotRead.model_validate(spot)


@router.get("/units/{unit_id}/parking-spots")
async def list_parking_spots(unit: MemberUnit, db: DbSession) -> list[ParkingSpotRead]:
    return [
        ParkingSpotRead.model_validate(s)
        for s in await service.list_parking_spots(db, unit)
    ]


@router.delete("/units/{unit_id}/parking-spots/{spot_id}", status_code=204)
async def remove_parking_spot(
    unit: UnitDep, spot_id: int, admin: AdminUser, db: DbSession
) -> None:
    if not await service.remove_parking_spot(db, unit, spot_id):
        raise HTTPException(status_code=404, detail="Parking spot not found")


# --- vehicles (residents register, unit members view) ---


@router.post("/units/{unit_id}/vehicles", status_code=201)
async def register_vehicle(
    payload: VehicleCreate, unit: ResidentUnit, db: DbSession
) -> VehicleRead:
    try:
        vehicle = await service.register_vehicle(db, unit, payload)
    except service.PlateTaken:
        raise HTTPException(
            status_code=409, detail="Plate already registered"
        ) from None
    return VehicleRead.model_validate(vehicle)


@router.get("/units/{unit_id}/vehicles")
async def list_vehicles(unit: MemberUnit, db: DbSession) -> list[VehicleRead]:
    return [
        VehicleRead.model_validate(v) for v in await service.list_vehicles(db, unit)
    ]


@router.delete("/units/{unit_id}/vehicles/{vehicle_id}", status_code=204)
async def remove_vehicle(unit: ResidentUnit, vehicle_id: int, db: DbSession) -> None:
    if not await service.remove_vehicle(db, unit, vehicle_id):
        raise HTTPException(status_code=404, detail="Vehicle not found")
