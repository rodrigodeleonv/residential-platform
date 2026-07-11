from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request: commits on success, rolls back on exception."""
    factory = request.app.state.session_factory
    async with factory() as session, session.begin():
        yield session


DbSession = Annotated[AsyncSession, Depends(get_session)]
