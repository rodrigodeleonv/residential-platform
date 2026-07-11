from typing import Annotated

from fastapi import Cookie, Depends, HTTPException

from app.db import DbSession
from app.modules.auth import service
from app.modules.users.models import Role, User

SESSION_COOKIE = "session"

SessionCookie = Annotated[str | None, Cookie(alias=SESSION_COOKIE)]


async def get_current_user(db: DbSession, session_token: SessionCookie = None) -> User:
    if session_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await service.get_user_by_session_token(db, session_token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_admin(user: CurrentUser) -> User:
    if Role.ADMIN not in user.roles:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


AdminUser = Annotated[User, Depends(get_current_admin)]
