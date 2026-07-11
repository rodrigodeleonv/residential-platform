from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin


class ParkingSpot(TimestampMixin, Base):
    """A numbered parking spot assigned to a unit (visitor spots live in units module)."""

    __tablename__ = "parking_spots"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"))
    number: Mapped[str] = mapped_column(unique=True)


class Vehicle(TimestampMixin, Base):
    """A resident vehicle. Units may register more vehicles than assigned spots."""

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"))
    plate: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None]
