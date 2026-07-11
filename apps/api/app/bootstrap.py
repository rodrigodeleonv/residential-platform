"""Create the first admin user (later admins are created through the API).

Usage: uv run python -m app.bootstrap <email> <full name>
"""

import asyncio
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.modules.users.models import Role, RoleAssignment, User


async def create_admin(email: str, full_name: str) -> None:
    engine = create_async_engine(get_settings().database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db, db.begin():
        db.add(
            User(
                email=email.lower(),
                full_name=full_name,
                role_assignments=[RoleAssignment(role=Role.ADMIN)],
            )
        )
    await engine.dispose()
    print(f"Admin {email} created. Log in via /auth/request-code.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    asyncio.run(create_admin(sys.argv[1], sys.argv[2]))
