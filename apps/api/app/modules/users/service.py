from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.email import EmailProvider
from app.modules.audit import service as audit
from app.modules.auth import service as auth
from app.modules.users.models import RoleAssignment, User
from app.modules.users.schemas import UserCreate


class EmailAlreadyRegistered(Exception):
    pass


async def create_user(
    db: AsyncSession,
    data: UserCreate,
    *,
    actor: User,
    provider: EmailProvider,
    settings: Settings,
) -> User:
    email = data.email.lower()
    if await db.scalar(select(User.id).where(User.email == email)) is not None:
        raise EmailAlreadyRegistered(email)

    user = User(
        email=email,
        full_name=data.full_name,
        phone=data.phone,
        role_assignments=[RoleAssignment(role=role) for role in data.roles],
    )
    db.add(user)
    await db.flush()
    await audit.record(
        db,
        "user_created",
        actor_id=actor.id,
        target_user_id=user.id,
        data={"roles": sorted(data.roles)},
    )
    if data.send_invitation:
        await auth.send_login_email(db, user, provider, settings, invitation=True)
    return user


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.scalars(select(User).order_by(User.id))
    return list(result)
