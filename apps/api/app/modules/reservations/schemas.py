from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.reservations.models import TimeSlot
from app.schemas import MoneyRead


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


class AreaRead(MoneyRead):
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


class ReservationRead(MoneyRead):
    id: int
    area_id: int
    unit_id: int
    user_id: int
    day: date
    slot: TimeSlot
    fee: Decimal
    canceled_at: datetime | None
