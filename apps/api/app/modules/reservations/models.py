from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin, str_enum


class TimeSlot(StrEnum):
    """The fixed 6-hour booking slots of a day; reservations always span a whole slot."""

    MORNING = "morning"  # 06:00-12:00
    AFTERNOON = "afternoon"  # 12:00-18:00
    EVENING = "evening"  # 18:00-24:00


class ReservableArea(TimestampMixin, Base):
    """A bookable common area; admins manage the catalog."""

    __tablename__ = "reservable_areas"
    __table_args__ = (
        CheckConstraint("capacity >= 1", name="capacity_min"),
        CheckConstraint("fee >= 0", name="fee_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None]
    capacity: Mapped[int] = mapped_column(default=1)  # parallel bookings per slot
    fee: Mapped[Decimal] = mapped_column(default=Decimal(0))  # per slot; 0 = free
    is_active: Mapped[bool] = mapped_column(default=True)


class Reservation(TimestampMixin, Base):
    """One slot of an area booked by a resident for their unit."""

    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    area_id: Mapped[int] = mapped_column(
        ForeignKey("reservable_areas.id", ondelete="CASCADE")
    )
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    day: Mapped[date]
    slot: Mapped[TimeSlot] = mapped_column(str_enum(TimeSlot, "time_slot"))
    fee: Mapped[Decimal]  # snapshot of the area fee at booking time (for billing)
    canceled_at: Mapped[datetime | None]
