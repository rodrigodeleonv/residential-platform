from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.vehicles.schemas import normalize_plate
from app.modules.visitors.models import PreRegKind


class PreRegistrationCreate(BaseModel):
    visitor_name: str
    visitor_plate: str | None = None
    kind: PreRegKind
    expiration_hours: int
    starts_at: datetime | None = None
    weekday: int | None = Field(default=None, ge=0, le=6)  # 0 = Monday
    time_of_day: time | None = None
    valid_from: date | None = None
    valid_until: date | None = None

    @field_validator("visitor_plate")
    @classmethod
    def _normalize_plate(cls, value: str | None) -> str | None:
        return normalize_plate(value) if value is not None else None

    @field_validator("starts_at")
    @classmethod
    def _require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("starts_at must include a timezone offset")
        return value

    @model_validator(mode="after")
    def _check_shape(self) -> PreRegistrationCreate:
        one_off_fields = self.starts_at is not None
        recurring_fields = [
            self.weekday,
            self.time_of_day,
            self.valid_from,
            self.valid_until,
        ]
        if self.kind is PreRegKind.ONE_OFF:
            if not one_off_fields or any(f is not None for f in recurring_fields):
                raise ValueError(
                    "a one-off pre-registration takes starts_at and nothing else"
                )
        else:
            if one_off_fields or any(f is None for f in recurring_fields):
                raise ValueError(
                    "a recurring pre-registration takes weekday, time_of_day,"
                    " valid_from and valid_until"
                )
            assert self.valid_from is not None and self.valid_until is not None
            if self.valid_until < self.valid_from:
                raise ValueError("valid_until must be on or after valid_from")
        return self


class PreRegistrationUpdate(BaseModel):
    visitor_name: str | None = None
    visitor_plate: str | None = None
    expiration_hours: int | None = None
    starts_at: datetime | None = None
    weekday: int | None = Field(default=None, ge=0, le=6)
    time_of_day: time | None = None
    valid_from: date | None = None
    valid_until: date | None = None

    @field_validator("visitor_plate")
    @classmethod
    def _normalize_plate(cls, value: str | None) -> str | None:
        return normalize_plate(value) if value is not None else None

    @field_validator("starts_at")
    @classmethod
    def _require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("starts_at must include a timezone offset")
        return value


class PreRegistrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: int
    created_by_id: int | None
    visitor_name: str
    visitor_plate: str | None
    kind: PreRegKind
    expiration_hours: int
    starts_at: datetime | None
    weekday: int | None
    time_of_day: time | None
    valid_from: date | None
    valid_until: date | None


class GatehouseResident(BaseModel):
    # user_id is an opaque reference so the guard can record who authorized an
    # entry (flow A); personal data stays restricted to name and phone.
    user_id: int
    full_name: str
    phone: str | None


class GatehouseUnitCard(BaseModel):
    """The restricted data subset a guard is allowed to see for a unit."""

    unit_id: int
    kind: str
    number: str
    building_name: str | None
    residents: list[GatehouseResident]
    plates: list[str]
    parking_spot_numbers: list[str]


class GatehouseUnitSummary(BaseModel):
    """Minimal unit info so the gatehouse can find a unit (no resident data)."""

    unit_id: int
    kind: str
    number: str
    building_name: str | None


class VisitEntryCreate(BaseModel):
    unit_id: int
    visitor_name: str
    visitor_plate: str | None = None
    visitor_spot_id: int | None = None
    authorized_by_user_id: int | None = None  # flow A: resident approved live
    preregistration_id: int | None = None  # flow B: valid pre-registration

    @field_validator("visitor_plate")
    @classmethod
    def _normalize_plate(cls, value: str | None) -> str | None:
        return normalize_plate(value) if value is not None else None

    @model_validator(mode="after")
    def _exactly_one_authorization(self) -> VisitEntryCreate:
        if (self.authorized_by_user_id is None) == (self.preregistration_id is None):
            raise ValueError(
                "provide exactly one of authorized_by_user_id (flow A)"
                " or preregistration_id (flow B)"
            )
        return self


class VisitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: int
    visitor_name: str
    visitor_plate: str | None
    visitor_spot_id: int | None
    guard_id: int | None
    authorized_by_id: int | None
    preregistration_id: int | None
    entered_at: datetime
    exited_at: datetime | None
