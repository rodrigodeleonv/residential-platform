from pydantic import BaseModel, ConfigDict, field_validator


def normalize_plate(value: str) -> str:
    plate = "".join(value.split()).upper()
    if not plate:
        raise ValueError("plate cannot be empty")
    return plate


class ParkingSpotCreate(BaseModel):
    number: str


class ParkingSpotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: int
    number: str


class VehicleCreate(BaseModel):
    plate: str
    description: str | None = None

    _normalize_plate = field_validator("plate")(normalize_plate)


class VehicleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: int
    plate: str
    description: str | None
