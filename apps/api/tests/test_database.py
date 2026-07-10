from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def test_session_runs_queries(db_session: AsyncSession) -> None:
    assert await db_session.scalar(text("SELECT 1")) == 1


async def test_migrations_are_applied(db_session: AsyncSession) -> None:
    version = await db_session.scalar(text("SELECT version_num FROM alembic_version"))
    assert version


async def test_writes_do_not_leak_between_tests(db_session: AsyncSession) -> None:
    await db_session.execute(text("CREATE TABLE leak_probe (id int)"))
    count = await db_session.scalar(
        text(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = 'leak_probe'"
        )
    )
    assert count == 1


async def test_previous_test_write_was_rolled_back(db_session: AsyncSession) -> None:
    count = await db_session.scalar(
        text(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = 'leak_probe'"
        )
    )
    assert count == 0
