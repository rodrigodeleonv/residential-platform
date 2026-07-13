from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin, str_enum


class ChargeKind(StrEnum):
    MAINTENANCE = "maintenance"
    RESERVATION = "reservation"
    FINE = "fine"


class InfractionType(TimestampMixin, Base):
    """Catalog entry admins issue fines from."""

    __tablename__ = "infraction_types"
    __table_args__ = (CheckConstraint("fine_amount > 0", name="fine_amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None]
    fine_amount: Mapped[Decimal]
    is_active: Mapped[bool] = mapped_column(default=True)


class Charge(TimestampMixin, Base):
    """Money a unit owes. View-only billing: admins mark payments manually."""

    __tablename__ = "charges"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint(
            "NOT (paid_at IS NOT NULL AND voided_at IS NOT NULL)",
            name="paid_or_voided",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"))
    kind: Mapped[ChargeKind] = mapped_column(str_enum(ChargeKind, "charge_kind"))
    description: Mapped[str]
    amount: Mapped[Decimal]  # snapshot at issue time
    reservation_id: Mapped[int | None] = mapped_column(
        ForeignKey("reservations.id", ondelete="SET NULL")
    )
    infraction_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("infraction_types.id")
    )
    paid_at: Mapped[datetime | None]
    voided_at: Mapped[datetime | None]  # e.g. its reservation was canceled unpaid
