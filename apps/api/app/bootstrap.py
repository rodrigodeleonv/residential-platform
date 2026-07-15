"""Create the first admin user (later admins are created through the API).

Usage: uv run python -m app.bootstrap <email> <full name>
"""

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.all_models  # noqa: F401  (RoleAssignment references other modules' tables)
from app.config import get_settings
from app.modules.users.models import Role, RoleAssignment, User


async def create_admin(email: str, full_name: str) -> None:
    email = email.lower()
    engine = create_async_engine(get_settings().database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db, db.begin():
        exists = await db.scalar(select(User.id).where(User.email == email)) is not None
        if not exists:
            db.add(
                User(
                    email=email,
                    full_name=full_name,
                    role_assignments=[RoleAssignment(role=Role.ADMIN)],
                )
            )
    await engine.dispose()
    if exists:
        print(f"User {email} already exists; nothing to do.")
    else:
        print(f"Admin {email} created. Log in via /auth/request-code.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    asyncio.run(create_admin(sys.argv[1], sys.argv[2]))
