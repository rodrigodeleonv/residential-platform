from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.billing.models import ChargeKind
from app.schemas import MoneyRead


class InfractionCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    fine_amount: Decimal = Field(gt=0)


class InfractionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    fine_amount: Decimal | None = Field(default=None, gt=0)
    is_active: bool | None = None


class InfractionRead(MoneyRead):
    id: int
    name: str
    description: str | None
    fine_amount: Decimal
    is_active: bool


class MaintenanceChargeCreate(BaseModel):
    description: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)


class FineCreate(BaseModel):
    infraction_type_id: int


class ChargeRead(MoneyRead):
    id: int
    unit_id: int
    kind: ChargeKind
    description: str
    amount: Decimal
    reservation_id: int | None
    infraction_type_id: int | None
    paid_at: datetime | None
    voided_at: datetime | None
    created_at: datetime


class StatementRead(BaseModel):
    """A unit's account: what it owes and what has been paid (owner/admin only)."""

    currency: str
    pending: list[ChargeRead]
    pending_total: Decimal
    paid: list[ChargeRead]
