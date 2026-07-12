from datetime import date

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.email import EmailProvider
from app.modules.audit import service as audit
from app.modules.auth import service as auth
from app.modules.units.models import Building, Unit, VisitorParkingSpot
from app.modules.units.schemas import TenancyUpdate, TenantRegister, UnitCreate
from app.modules.users.models import Role, RoleAssignment, User


class NameTaken(Exception):
    pass


class BuildingNotFound(Exception):
    pass


class AlreadyAssigned(Exception):
    pass


class InvalidTenancyRange(Exception):
    pass


# --- physical structure ---


async def create_building(db: AsyncSession, name: str) -> Building:
    if await db.scalar(select(Building.id).where(Building.name == name)) is not None:
        raise NameTaken(name)
    building = Building(name=name)
    db.add(building)
    await db.flush()
    return building


async def list_buildings(db: AsyncSession) -> list[Building]:
    return list(await db.scalars(select(Building).order_by(Building.id)))


async def create_unit(db: AsyncSession, data: UnitCreate) -> Unit:
    if (
        data.building_id is not None
        and await db.get(Building, data.building_id) is None
    ):
        raise BuildingNotFound(data.building_id)
    taken = await db.scalar(
        select(Unit.id).where(
            Unit.building_id.is_(None)
            if data.building_id is None
            else Unit.building_id == data.building_id,
            Unit.number == data.number,
        )
    )
    if taken is not None:
        raise NameTaken(data.number)
    unit = Unit(
        kind=data.kind,
        building_id=data.building_id,
        floor=data.floor,
        number=data.number,
    )
    db.add(unit)
    await db.flush()
    return unit


async def list_units(db: AsyncSession) -> list[Unit]:
    return list(await db.scalars(select(Unit).order_by(Unit.id)))


async def create_visitor_spot(db: AsyncSession, number: str) -> VisitorParkingSpot:
    exists = await db.scalar(
        select(VisitorParkingSpot.id).where(VisitorParkingSpot.number == number)
    )
    if exists is not None:
        raise NameTaken(number)
    spot = VisitorParkingSpot(number=number)
    db.add(spot)
    await db.flush()
    return spot


async def list_visitor_spots(db: AsyncSession) -> list[VisitorParkingSpot]:
    return list(
        await db.scalars(select(VisitorParkingSpot).order_by(VisitorParkingSpot.id))
    )


# --- ownership ---


async def assign_owner(
    db: AsyncSession, unit: Unit, user: User, actor: User
) -> RoleAssignment:
    exists = await db.scalar(
        select(RoleAssignment.id).where(
            RoleAssignment.user_id == user.id,
            RoleAssignment.role == Role.OWNER,
            RoleAssignment.unit_id == unit.id,
        )
    )
    if exists is not None:
        raise AlreadyAssigned
    assignment = RoleAssignment(user_id=user.id, role=Role.OWNER, unit_id=unit.id)
    db.add(assignment)
    await db.flush()
    await audit.record(
        db,
        "owner_assigned",
        actor_id=actor.id,
        target_user_id=user.id,
        data={"unit_id": unit.id},
    )
    return assignment


async def remove_owner(db: AsyncSession, unit: Unit, user_id: int, actor: User) -> bool:
    assignment = await db.scalar(
        select(RoleAssignment).where(
            RoleAssignment.user_id == user_id,
            RoleAssignment.role == Role.OWNER,
            RoleAssignment.unit_id == unit.id,
        )
    )
    if assignment is None:
        return False
    await db.delete(assignment)
    await audit.record(
        db,
        "owner_removed",
        actor_id=actor.id,
        target_user_id=user_id,
        data={"unit_id": unit.id},
    )
    return True


async def owners_of(db: AsyncSession, unit: Unit) -> list[User]:
    return list(
        await db.scalars(
            select(User)
            .join(RoleAssignment)
            .where(RoleAssignment.role == Role.OWNER, RoleAssignment.unit_id == unit.id)
            .order_by(User.id)
        )
    )


async def is_owner(db: AsyncSession, user_id: int, unit_id: int) -> bool:
    return (
        await db.scalar(
            select(RoleAssignment.id).where(
                RoleAssignment.user_id == user_id,
                RoleAssignment.role == Role.OWNER,
                RoleAssignment.unit_id == unit_id,
            )
        )
        is not None
    )


# --- tenancy & occupancy ---


def _active_tenancy_clause(on: date) -> ColumnElement[bool]:
    return and_(
        RoleAssignment.role == Role.TENANT,
        RoleAssignment.starts_on <= on,
        RoleAssignment.ends_on >= on,
    )


async def active_tenancies(
    db: AsyncSession, unit_id: int, on: date
) -> list[RoleAssignment]:
    return list(
        await db.scalars(
            select(RoleAssignment).where(
                RoleAssignment.unit_id == unit_id, _active_tenancy_clause(on)
            )
        )
    )


async def residents_of(
    db: AsyncSession, unit: Unit, on: date | None = None
) -> list[User]:
    """The responsible persons who actually occupy the unit right now."""
    on = on or date.today()
    tenancies = await active_tenancies(db, unit.id, on)
    if tenancies:
        return [tenancy.user for tenancy in tenancies]
    return await owners_of(db, unit)


async def is_resident(
    db: AsyncSession, user_id: int, unit_id: int, on: date | None = None
) -> bool:
    """Whoever actually resides: active tenants if any exist, owners otherwise."""
    on = on or date.today()
    tenancies = await active_tenancies(db, unit_id, on)
    if tenancies:
        return any(tenancy.user_id == user_id for tenancy in tenancies)
    return await is_owner(db, user_id, unit_id)


async def units_of(
    db: AsyncSession, user_id: int, on: date | None = None
) -> list[Unit]:
    """Units the user belongs to: owned ones plus active tenancies."""
    on = on or date.today()
    return list(
        await db.scalars(
            select(Unit)
            .join(RoleAssignment, RoleAssignment.unit_id == Unit.id)
            .where(
                RoleAssignment.user_id == user_id,
                or_(RoleAssignment.role == Role.OWNER, _active_tenancy_clause(on)),
            )
            .distinct()
            .order_by(Unit.id)
        )
    )


async def register_tenant(
    db: AsyncSession,
    unit: Unit,
    data: TenantRegister,
    *,
    actor: User,
    provider: EmailProvider,
    settings: Settings,
) -> RoleAssignment:
    email = data.email.lower()
    user = await db.scalar(select(User).where(User.email == email))
    is_new_user = user is None
    if user is None:
        user = User(email=email, full_name=data.full_name, phone=data.phone)
        db.add(user)
        await db.flush()

    exists = await db.scalar(
        select(RoleAssignment.id).where(
            RoleAssignment.user_id == user.id,
            RoleAssignment.role == Role.TENANT,
            RoleAssignment.unit_id == unit.id,
        )
    )
    if exists is not None:
        raise AlreadyAssigned

    tenancy = RoleAssignment(
        user=user,  # relationship, not just the FK: responses serialize tenancy.user
        role=Role.TENANT,
        unit_id=unit.id,
        starts_on=data.starts_on,
        ends_on=data.ends_on,
    )
    db.add(tenancy)
    await db.flush()
    # Reload the collection here (async) so serializing user.roles needs no lazy IO.
    await db.refresh(user, ["role_assignments"])
    await audit.record(
        db,
        "tenant_registered",
        actor_id=actor.id,
        target_user_id=user.id,
        data={
            "unit_id": unit.id,
            "starts_on": str(data.starts_on),
            "ends_on": str(data.ends_on),
        },
    )
    if is_new_user and data.send_invitation:
        await auth.send_login_email(db, user, provider, settings, invitation=True)
    return tenancy


async def get_tenancy(
    db: AsyncSession, unit_id: int, tenancy_id: int
) -> RoleAssignment | None:
    return await db.scalar(
        select(RoleAssignment).where(
            RoleAssignment.id == tenancy_id,
            RoleAssignment.role == Role.TENANT,
            RoleAssignment.unit_id == unit_id,
        )
    )


async def list_tenancies(db: AsyncSession, unit: Unit) -> list[RoleAssignment]:
    return list(
        await db.scalars(
            select(RoleAssignment)
            .where(
                RoleAssignment.role == Role.TENANT, RoleAssignment.unit_id == unit.id
            )
            .order_by(RoleAssignment.id)
        )
    )


async def update_tenancy(
    db: AsyncSession, tenancy: RoleAssignment, data: TenancyUpdate, actor: User
) -> RoleAssignment:
    starts_on = data.starts_on or tenancy.starts_on
    ends_on = data.ends_on or tenancy.ends_on
    assert starts_on is not None and ends_on is not None  # tenants always have dates
    if ends_on < starts_on:
        raise InvalidTenancyRange
    tenancy.starts_on, tenancy.ends_on = starts_on, ends_on
    await audit.record(
        db,
        "tenant_updated",
        actor_id=actor.id,
        target_user_id=tenancy.user_id,
        data={
            "unit_id": tenancy.unit_id,
            "starts_on": str(starts_on),
            "ends_on": str(ends_on),
        },
    )
    await db.flush()
    return tenancy


async def revoke_tenancy(
    db: AsyncSession, tenancy: RoleAssignment, actor: User
) -> None:
    await audit.record(
        db,
        "tenant_revoked",
        actor_id=actor.id,
        target_user_id=tenancy.user_id,
        data={"unit_id": tenancy.unit_id},
    )
    await db.delete(tenancy)
