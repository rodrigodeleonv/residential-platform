from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, model_validator

from app.modules.units.models import UnitKind
from app.modules.users.schemas import UserRead


class BuildingCreate(BaseModel):
    name: str


class BuildingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class UnitCreate(BaseModel):
    kind: UnitKind
    building_id: int | None = None
    floor: int | None = None
    number: str

    @model_validator(mode="after")
    def check_shape(self) -> UnitCreate:
        if self.kind is UnitKind.APARTMENT and (
            self.building_id is None or self.floor is None
        ):
            raise ValueError("an apartment requires building_id and floor")
        if self.kind is UnitKind.HOUSE and (
            self.building_id is not None or self.floor is not None
        ):
            raise ValueError("a house cannot have building_id or floor")
        return self


class UnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: UnitKind
    building_id: int | None
    floor: int | None
    number: str


class VisitorParkingSpotCreate(BaseModel):
    number: str


class VisitorParkingSpotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str


class OwnerAssign(BaseModel):
    user_id: int


class TenantRegister(BaseModel):
    email: EmailStr
    full_name: str
    phone: str | None = None
    starts_on: date
    ends_on: date
    send_invitation: bool = True

    @model_validator(mode="after")
    def check_range(self) -> TenantRegister:
        if self.ends_on < self.starts_on:
            raise ValueError("ends_on must be on or after starts_on")
        return self


class TenancyUpdate(BaseModel):
    starts_on: date | None = None
    ends_on: date | None = None


class TenancyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user: UserRead
    starts_on: date
    ends_on: date
