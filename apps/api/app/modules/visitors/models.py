from datetime import date, datetime, time
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin, str_enum


class PreRegKind(StrEnum):
    ONE_OFF = "one_off"
    RECURRING = "recurring"


class VisitPreRegistration(TimestampMixin, Base):
    """A resident's advance authorization for a visitor.

    One-off: a start moment plus an expiration window. Recurring: a weekday +
    time-of-day repeated over a bounded date range. The guard-visible window is
    always computed at query time, never stored.
    """

    __tablename__ = "visit_preregistrations"
    __table_args__ = (
        CheckConstraint(
            "(kind = 'one_off' AND starts_at IS NOT NULL AND weekday IS NULL"
            " AND time_of_day IS NULL AND valid_from IS NULL AND valid_until IS NULL)"
            " OR (kind = 'recurring' AND starts_at IS NULL AND weekday IS NOT NULL"
            " AND time_of_day IS NOT NULL AND valid_from IS NOT NULL AND valid_until IS NOT NULL)",
            name="kind_shape",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"))
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    visitor_name: Mapped[str]
    visitor_plate: Mapped[str | None]
    kind: Mapped[PreRegKind] = mapped_column(str_enum(PreRegKind, "prereg_kind"))
    expiration_hours: Mapped[int]
    starts_at: Mapped[datetime | None]
    weekday: Mapped[int | None]  # 0 = Monday ... 6 = Sunday
    time_of_day: Mapped[time | None]
    valid_from: Mapped[date | None]
    valid_until: Mapped[date | None]


class VisitLog(TimestampMixin, Base):
    """Gatehouse record of a visitor entry (and later, exit).

    Every entry carries exactly who authorized it: a resident who approved live
    (flow A) or a valid pre-registration (flow B).
    """

    __tablename__ = "visit_log"
    __table_args__ = (
        CheckConstraint(
            "authorized_by_id IS NOT NULL OR preregistration_id IS NOT NULL",
            name="authorization_present",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"))
    visitor_name: Mapped[str]
    visitor_plate: Mapped[str | None]
    visitor_spot_id: Mapped[int | None] = mapped_column(
        ForeignKey("visitor_parking_spots.id", ondelete="SET NULL")
    )
    guard_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    authorized_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    preregistration_id: Mapped[int | None] = mapped_column(
        ForeignKey("visit_preregistrations.id", ondelete="SET NULL")
    )
    entered_at: Mapped[datetime]
    exited_at: Mapped[datetime | None]
