# Residential Platform — API

FastAPI backend. See the [root README](../../README.md) for the project overview and quickstart, and [`docs/implementation-guide.md`](../../docs/implementation-guide.md) for code structure and conventions.

## Layout

- `app/main.py` — app factory (`create_app`); routers mount under `/api/v0`
- `app/config.py` — settings from env vars (`APP_*` prefix) or `.env`
- `app/db.py` — per-request database session dependency
- `app/models.py` — SQLAlchemy declarative base (naming conventions, timestamps)
- `app/modules/` — domain modules (router → service → models per module)
- `migrations/` — Alembic migrations
- `tests/` — pytest suite

## Common tasks

```bash
uv sync                                        # install dependencies
uv run uvicorn app.main:app --reload           # run locally (needs compose postgres)
uv run pytest                                  # tests (creates/migrates residential_test db)
uv run alembic upgrade head                    # apply migrations
uv run alembic revision --autogenerate -m "…"  # new migration (review it!)
```

Tests expect the compose PostgreSQL on `localhost:5432`; they create a separate `residential_test` database, migrate it to head, and roll back every test's writes.
