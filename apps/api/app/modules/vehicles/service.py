from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.units.models import Unit
from app.modules.vehicles.models import ParkingSpot, Vehicle
from app.modules.vehicles.schemas import VehicleCreate


class NumberTaken(Exception):
    pass


class SpotLimitReached(Exception):
    pass


class PlateTaken(Exception):
    pass


async def add_parking_spot(
    db: AsyncSession, unit: Unit, number: str, settings: Settings
) -> ParkingSpot:
    if (
        await db.scalar(select(ParkingSpot.id).where(ParkingSpot.number == number))
        is not None
    ):
        raise NumberTaken(number)
    assigned = await db.scalar(
        select(func.count())
        .select_from(ParkingSpot)
        .where(ParkingSpot.unit_id == unit.id)
    )
    if assigned is not None and assigned >= settings.parking_spots_per_unit:
        raise SpotLimitReached
    spot = ParkingSpot(unit_id=unit.id, number=number)
    db.add(spot)
    await db.flush()
    return spot


async def list_parking_spots(db: AsyncSession, unit: Unit) -> list[ParkingSpot]:
    return list(
        await db.scalars(
            select(ParkingSpot)
            .where(ParkingSpot.unit_id == unit.id)
            .order_by(ParkingSpot.id)
        )
    )


async def remove_parking_spot(db: AsyncSession, unit: Unit, spot_id: int) -> bool:
    spot = await db.scalar(
        select(ParkingSpot).where(
            ParkingSpot.id == spot_id, ParkingSpot.unit_id == unit.id
        )
    )
    if spot is None:
        return False
    await db.delete(spot)
    return True


async def register_vehicle(
    db: AsyncSession, unit: Unit, data: VehicleCreate
) -> Vehicle:
    if (
        await db.scalar(select(Vehicle.id).where(Vehicle.plate == data.plate))
        is not None
    ):
        raise PlateTaken(data.plate)
    vehicle = Vehicle(unit_id=unit.id, plate=data.plate, description=data.description)
    db.add(vehicle)
    await db.flush()
    return vehicle


async def list_vehicles(db: AsyncSession, unit: Unit) -> list[Vehicle]:
    return list(
        await db.scalars(
            select(Vehicle).where(Vehicle.unit_id == unit.id).order_by(Vehicle.id)
        )
    )


async def remove_vehicle(db: AsyncSession, unit: Unit, vehicle_id: int) -> bool:
    vehicle = await db.scalar(
        select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.unit_id == unit.id)
    )
    if vehicle is None:
        return False
    await db.delete(vehicle)
    return True
