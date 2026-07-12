from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from app.modules.reservations.models import TimeSlot


class AreaCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    capacity: int = Field(default=1, ge=1)
    fee: Decimal = Field(default=Decimal(0), ge=0)


class AreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    capacity: int | None = Field(default=None, ge=1)
    fee: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None


class _MoneyRead(BaseModel):
    """Read schema whose amounts carry the deployment-wide currency."""

    model_config = ConfigDict(from_attributes=True)

    currency: str = ""

    @classmethod
    def of(cls, obj: object, currency: str) -> Self:
        read = cls.model_validate(obj)
        read.currency = currency
        return read


class AreaRead(_MoneyRead):
    id: int
    name: str
    description: str | None
    capacity: int
    fee: Decimal
    is_active: bool


class SlotAvailability(BaseModel):
    slot: TimeSlot
    capacity: int
    booked: int
    available: int


class ReservationCreate(BaseModel):
    area_id: int
    day: date
    slot: TimeSlot


class ReservationRead(_MoneyRead):
    id: int
    area_id: int
    unit_id: int
    user_id: int
    day: date
    slot: TimeSlot
    fee: Decimal
    canceled_at: datetime | None
