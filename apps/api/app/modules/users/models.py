from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin


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
    can be admin and owner at once. Owner/tenant get a unit scope in Phase 2."""

    __tablename__ = "role_assignments"
    __table_args__ = (UniqueConstraint("user_id", "role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[Role] = mapped_column(
        Enum(
            Role,
            name="role",
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        )
    )

    user: Mapped[User] = relationship(back_populates="role_assignments")
