from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, str_enum


class UnitKind(StrEnum):
    APARTMENT = "apartment"
    HOUSE = "house"


class Building(TimestampMixin, Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)

    units: Mapped[list[Unit]] = relationship(back_populates="building")


class Unit(TimestampMixin, Base):
    """A dwelling: an apartment inside a building or a standalone house."""

    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("building_id", "number", postgresql_nulls_not_distinct=True),
        CheckConstraint(
            "(kind = 'apartment' AND building_id IS NOT NULL AND floor IS NOT NULL)"
            " OR (kind = 'house' AND building_id IS NULL AND floor IS NULL)",
            name="kind_shape",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[UnitKind] = mapped_column(str_enum(UnitKind, "unit_kind"))
    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="RESTRICT")
    )
    floor: Mapped[int | None]
    number: Mapped[str]

    building: Mapped[Building | None] = relationship(
        back_populates="units", lazy="selectin"
    )


class VisitorParkingSpot(TimestampMixin, Base):
    """Temporary parking for visitors; assignment happens in the gatehouse flows."""

    __tablename__ = "visitor_parking_spots"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(unique=True)
