from typing import Annotated

from fastapi import Depends, HTTPException

from app.db import DbSession
from app.modules.auth.deps import CurrentUser
from app.modules.units import service
from app.modules.units.models import Unit
from app.modules.users.models import Role


async def get_unit_or_404(unit_id: int, db: DbSession) -> Unit:
    unit = await db.get(Unit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


UnitDep = Annotated[Unit, Depends(get_unit_or_404)]


async def get_managed_unit(unit: UnitDep, user: CurrentUser, db: DbSession) -> Unit:
    """A unit the current user may manage tenants for: one of its owners, or an admin."""
    if Role.ADMIN in user.roles or await service.is_owner(db, user.id, unit.id):
        return unit
    raise HTTPException(status_code=403, detail="Owner of this unit or admin required")


ManagedUnit = Annotated[Unit, Depends(get_managed_unit)]


async def get_member_unit(unit: UnitDep, user: CurrentUser, db: DbSession) -> Unit:
    """A unit the current user belongs to (owner or active tenant), or any unit for admins.

    Grants read access to unit data (parking spots, vehicles, ...).
    """
    if (
        Role.ADMIN in user.roles
        or await service.is_owner(db, user.id, unit.id)
        or await service.is_resident(db, user.id, unit.id)
    ):
        return unit
    raise HTTPException(status_code=403, detail="Member of this unit or admin required")


MemberUnit = Annotated[Unit, Depends(get_member_unit)]


async def get_resident_unit(unit: UnitDep, user: CurrentUser, db: DbSession) -> Unit:
    """A unit the current user actually resides in, or any unit for admins.

    Resident-only actions (vehicles, reservations, visitor pre-registration)
    belong to whoever occupies the unit: a non-resident owner is rejected.
    """
    if Role.ADMIN in user.roles or await service.is_resident(db, user.id, unit.id):
        return unit
    raise HTTPException(
        status_code=403, detail="Resident of this unit or admin required"
    )


ResidentUnit = Annotated[Unit, Depends(get_resident_unit)]
