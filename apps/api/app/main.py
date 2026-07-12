from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import health
from app.config import API_PREFIX, Settings, get_settings
from app.email import create_email_provider
from app.modules.auth.router import router as auth_router
from app.modules.units.router import router as units_router
from app.modules.users.router import router as users_router
from app.modules.vehicles.router import router as vehicles_router
from app.modules.visitors.router import router as visitors_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine = create_async_engine(settings.database_url)
    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    yield
    await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Residential Platform API", lifespan=lifespan)
    app.state.settings = settings or get_settings()
    app.state.email_provider = create_email_provider(app.state.settings)
    for router in (
        health.router,
        auth_router,
        users_router,
        units_router,
        vehicles_router,
        visitors_router,
    ):
        app.include_router(router, prefix=API_PREFIX)
    return app


app = create_app()
