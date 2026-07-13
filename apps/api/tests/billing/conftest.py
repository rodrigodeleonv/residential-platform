from collections.abc import Awaitable, Callable
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.models import Charge, ChargeKind, InfractionType
from app.modules.reservations.models import ReservableArea
from app.modules.units.models import Unit
from app.modules.users.models import Role, User
from tests.conftest import RoleGranter, UnitFactory, UserFactory

type InfractionFactory = Callable[..., Awaitable[InfractionType]]
type ChargeFactory = Callable[..., Awaitable[Charge]]
type AreaFactory = Callable[..., Awaitable[ReservableArea]]
type OwnerFactory = Callable[..., Awaitable[tuple[User, Unit]]]


@pytest.fixture
def create_infraction(db_session: AsyncSession) -> InfractionFactory:
    async def _create(
        name: str = "Noise after hours",
        *,
        fine_amount: Decimal = Decimal("100.00"),
        is_active: bool = True,
    ) -> InfractionType:
        infraction = InfractionType(
            name=name, fine_amount=fine_amount, is_active=is_active
        )
        db_session.add(infraction)
        await db_session.flush()
        return infraction

    return _create


@pytest.fixture
def create_charge(db_session: AsyncSession) -> ChargeFactory:
    async def _create(
        unit: Unit,
        *,
        kind: ChargeKind = ChargeKind.MAINTENANCE,
        description: str = "Maintenance fee",
        amount: Decimal = Decimal("300.00"),
    ) -> Charge:
        charge = Charge(
            unit_id=unit.id, kind=kind, description=description, amount=amount
        )
        db_session.add(charge)
        await db_session.flush()
        return charge

    return _create


@pytest.fixture
def create_area(db_session: AsyncSession) -> AreaFactory:
    async def _create(
        name: str = "Clubhouse", *, fee: Decimal = Decimal("150.00")
    ) -> ReservableArea:
        area = ReservableArea(name=name, capacity=1, fee=fee)
        db_session.add(area)
        await db_session.flush()
        return area

    return _create


@pytest.fixture
def make_owner(
    create_user: UserFactory, create_unit: UnitFactory, grant_role: RoleGranter
) -> OwnerFactory:
    """An owner-occupant with their unit (owners are who read the statement)."""

    async def _make(
        email: str = "owner@example.com", number: str = "H-1"
    ) -> tuple[User, Unit]:
        user = await create_user(email)
        unit = await create_unit(number)
        await grant_role(user, Role.OWNER, unit)
        return user, unit

    return _make
