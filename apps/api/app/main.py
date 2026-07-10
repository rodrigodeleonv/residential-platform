from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import health
from app.config import Settings, get_settings

API_PREFIX = "/api/v0"


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
    app.include_router(health.router, prefix=API_PREFIX)
    return app


app = create_app()
