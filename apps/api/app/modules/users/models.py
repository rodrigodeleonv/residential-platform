from datetime import date
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, str_enum


class Role(StrEnum):
    ADMIN = "admin"
    OWNER = "owner"
    TENANT = "tenant"
    GUARD = "guard"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    full_name: Mapped[str]
    phone: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)

    role_assignments: Mapped[list[RoleAssignment]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def roles(self) -> set[Role]:
        return {assignment.role for assignment in self.role_assignments}


class RoleAssignment(Base):
    """A role held by a user. Roles are assignments, not user types: one person
    can be admin and owner at once.

    Admin/guard are condominium-wide (no unit). Owner/tenant are scoped to a
    unit; tenant additionally carries the contract date range, and occupancy is
    derived from it: a unit with an active tenancy is tenant-occupied, otherwise
    owner-occupied (this enforces the owners-XOR-tenants rule without extra state).
    """

    __tablename__ = "role_assignments"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "role", "unit_id", postgresql_nulls_not_distinct=True
        ),
        CheckConstraint(
            "(role IN ('admin', 'guard') AND unit_id IS NULL"
            " AND starts_on IS NULL AND ends_on IS NULL)"
            " OR (role = 'owner' AND unit_id IS NOT NULL"
            " AND starts_on IS NULL AND ends_on IS NULL)"
            " OR (role = 'tenant' AND unit_id IS NOT NULL"
            " AND starts_on IS NOT NULL AND ends_on IS NOT NULL)",
            name="role_scope",
        ),
        CheckConstraint(
            "ends_on IS NULL OR ends_on >= starts_on", name="tenancy_range"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[Role] = mapped_column(str_enum(Role, "role"))
    unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("units.id", ondelete="CASCADE")
    )
    starts_on: Mapped[date | None]
    ends_on: Mapped[date | None]

    user: Mapped[User] = relationship(
        back_populates="role_assignments", lazy="selectin"
    )
