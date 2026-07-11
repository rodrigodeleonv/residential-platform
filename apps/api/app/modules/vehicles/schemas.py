from pydantic import BaseModel, ConfigDict, field_validator


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

    @field_validator("plate")
    @classmethod
    def normalize_plate(cls, value: str) -> str:
        plate = "".join(value.split()).upper()
        if not plate:
            raise ValueError("plate cannot be empty")
        return plate


class VehicleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: int
    plate: str
    description: str | None
