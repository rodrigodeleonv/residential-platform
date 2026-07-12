from collections.abc import Awaitable, Callable
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reservations.models import ReservableArea
from app.modules.units.models import Unit
from app.modules.users.models import Role, User
from tests.conftest import RoleGranter, UnitFactory, UserFactory

type AreaFactory = Callable[..., Awaitable[ReservableArea]]
type ResidentFactory = Callable[..., Awaitable[tuple[User, Unit]]]


@pytest.fixture
def create_area(db_session: AsyncSession) -> AreaFactory:
    async def _create(
        name: str = "Lounge",
        *,
        capacity: int = 1,
        fee: Decimal = Decimal(0),
        is_active: bool = True,
    ) -> ReservableArea:
        area = ReservableArea(
            name=name, capacity=capacity, fee=fee, is_active=is_active
        )
        db_session.add(area)
        await db_session.flush()
        return area

    return _create


@pytest.fixture
def make_resident(
    create_user: UserFactory, create_unit: UnitFactory, grant_role: RoleGranter
) -> ResidentFactory:
    """An owner-occupant with their unit (the common booking actor)."""

    async def _make(
        email: str = "resident@example.com", number: str = "H-1"
    ) -> tuple[User, Unit]:
        user = await create_user(email)
        unit = await create_unit(number)
        await grant_role(user, Role.OWNER, unit)
        return user, unit

    return _make
