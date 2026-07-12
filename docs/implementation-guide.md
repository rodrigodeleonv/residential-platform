# Residential Platform — Implementation Guide

Companion to `docs/development-plan.md`. The plan says **what** to build and in which order; this guide says **how**: code structure, conventions, and concrete steps. Business rules live in `requeriments.md` (Spanish, gitignored) — when in doubt, that file wins.

> **Working document**: this guide exists to bootstrap development. Once the codebase itself demonstrates these patterns, it will likely be deleted rather than maintained.

## 1. Backend project layout (`apps/api/`)

Modular monolith: code is organized by domain module, each module owns its full vertical slice.

```
apps/api/
├── pyproject.toml
├── alembic.ini
├── migrations/               # Alembic migrations (single history for the whole app)
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py               # create_app() factory + router registration
│   ├── config.py             # Settings (pydantic-settings), loaded from env/.env
│   ├── db.py                 # async engine, session factory, get_session dependency
│   ├── models.py             # DeclarativeBase + shared columns (id, created_at, updated_at)
│   └── modules/
│       ├── auth/             # login codes, magic links, sessions, current-user deps
│       ├── users/            # accounts, role assignments, onboarding/invitations
│       ├── units/            # buildings, floors, units, houses, ownership, tenancy
│       ├── vehicles/         # vehicle registry, parking spots
│       ├── visitors/         # pre-registrations, gatehouse flows, entry/exit log
│       ├── reservations/     # reservable areas, bookings
│       ├── billing/          # charges, fines, infraction catalog (view-only)
│       └── audit/            # audit log writer + query endpoints
└── tests/
    ├── conftest.py           # app + db fixtures
    └── <module>/             # tests mirror the module layout
```

Each module contains (only the files it needs):

| File | Responsibility |
|---|---|
| `router.py` | HTTP endpoints. Thin: parse/validate, call service, shape response. |
| `schemas.py` | Pydantic request/response models. |
| `models.py` | SQLAlchemy models owned by this module. |
| `service.py` | Business rules. Receives an `AsyncSession`, returns domain objects. |

Rules of thumb:

- Routers never touch the session directly for business logic — services do.
- No repository layer: services use SQLAlchemy sessions directly.
- Cross-module calls go through the other module's `service.py` (never its router).
- The `audit` module exposes `audit.service.record(...)`; other services call it inside the same transaction.

## 2. Conventions

- **API prefix**: every router is mounted under `/api/v0` (single constant in `main.py`). Route paths inside modules are written without the prefix.
- **Resource naming**: plural nouns, kebab-free (`/api/v0/units/{unit_id}/vehicles`).
- **Primary keys**: integer autoincrement. Single deployment, a few hundred users — UUIDs add nothing here.
- **Timestamps**: `created_at` / `updated_at`, timezone-aware UTC (`TIMESTAMPTZ`). All server logic in UTC; the frontend localizes.
- **Errors**: raise `HTTPException` from routers; services raise small domain exceptions (e.g. `NotFoundError`, `PermissionDeniedError`) translated to HTTP codes by shared exception handlers in `main.py`.
- **Datetimes in APIs**: ISO 8601 with offset.
- **SQLAlchemy naming convention**: set the standard `MetaData(naming_convention=...)` dict on the base so Alembic autogenerate produces stable constraint names.
- **Language**: all code, comments, docstrings, and identifiers in English.

## 3. Configuration

`app/config.py` with `pydantic-settings`:

- `Settings` class reading env vars (prefix `APP_`), with a `.env` file for local dev (gitignored; keep `example.env` tracked).
- Minimum settings: `database_url`, `environment` (`local`/`production`), `session_ttl`, `email_provider` (`console` for now), cookie security flags.
- The app factory takes an optional `Settings` so tests can inject their own.

## 4. Database & migrations

- SQLAlchemy 2.0 **async** (`asyncpg` driver), `async_sessionmaker`, one session per request via a `get_session` FastAPI dependency (commit on success, rollback on exception).
- Alembic with async engine template. Workflow:
  1. Edit/add models in the module's `models.py`.
  2. `uv run alembic revision --autogenerate -m "<change>"` — always review the generated file.
  3. `uv run alembic upgrade head`.
- Migrations run explicitly (locally and on deploy), never automatically at app startup.

## 5. Auth implementation (Phase 1)

Passwordless, two doors into the same mechanism:

1. **Request code**: `POST /api/v0/auth/request-code` with email. If the user exists and is active, create a one-time code: 6 digits, stored **hashed**, expires in 10 minutes, max 5 verification attempts. Send via the email provider both the code and a magic link carrying a random token (same record). Always respond 200 (do not leak which emails exist).
2. **Verify**: `POST /api/v0/auth/verify` with email + code (or `GET` magic-link token). On success: invalidate the code, create a session.
3. **Sessions**: server-side `sessions` table (random token, user_id, expiry). Cookie: httpOnly, `SameSite=Lax`, `Secure` in production. Logout deletes the session row.
4. **Current user deps** in `modules/auth/deps.py`: `get_current_user`, `require_admin`, `require_guard`, `require_resident_of(unit_id)` (owner-occupant or active tenant), `require_owner_of(unit_id)`.

**Roles are assignments, not user types**: a `role_assignments` table (`user_id`, `role`, optional `unit_id` scope for owner/tenant). One person can be admin + owner at once. Tenant assignments carry the contract date range; expiry is enforced at authorization time (an expired tenancy simply fails the check — no background job needed).

**Audit**: login/logout events and any account change performed on *another* user's account are recorded via `audit.service.record`.

## 6. Email abstraction

- `EmailProvider` protocol with a single `send(to, subject, body)` (or a small message dataclass).
- `ConsoleEmailProvider` prints to stdout/log — the only implementation for now.
- Selected by `Settings.email_provider`; injected as a FastAPI dependency so tests can capture sent messages with a fake.

## 7. Testing

- **Runner**: pytest + `httpx.AsyncClient` over `ASGITransport` (no live server), `pytest-asyncio` (or anyio) for async tests.
- **DB fixture**: a dedicated test database (e.g. `residential_test` in the same compose Postgres). Per test: open a connection, begin an outer transaction, bind the session to it, roll back at teardown — fast and isolated. Schema created from migrations once per session.
- **What to test per feature** (definition of done):
  - Service-level tests for the business rules (the interesting logic).
  - Router-level tests for authz (who can/can't call it) and the happy path.
  - E2e (Playwright) only for critical flows, added in Phase 8.
- Fixtures for common actors: `admin_user`, `owner_with_unit`, `tenant_user`, `guard_user`, each returning an authenticated client.

## 8. Docker Compose

`docker-compose.yml` at the repo root:

- `postgres`: official `postgres:17` image, volume for data, healthcheck.
- `api`: built from `apps/api/Dockerfile` (uv-based multi-stage: sync deps, run `uvicorn app.main:app`), depends on postgres healthy.
- `web`: added in Phase 4 (build static assets, serve + proxy `/api` to the api service).

Local dev can also run the API directly (`uv run uvicorn app.main:create_app --factory --reload`) against the compose Postgres only.

## 9. CI (GitHub Actions)

Single workflow, triggered on push/PR:

- **backend** job: install uv → `uv sync` → `uv run ruff check .` → `uv run ruff format --check .` → `uv run pyright` → `uv run pytest` with a Postgres service container.
- **frontend** job (once `apps/web` exists): `npm ci` → lint → typecheck → `vitest run`.
- Path filters so backend-only changes don't run frontend jobs and vice versa.

## 10. Step-by-step: finishing Phase 0

Ordered, each step small and committable:

1. **App skeleton**: replace the hello-world `main.py` with the `app/` package — `create_app()` factory, `Settings`, `/api/v0/health` endpoint. Add `uvicorn` and `pydantic-settings` deps. Test: health returns 200.
2. **Compose + DB deps**: `docker-compose.yml` with Postgres; add `sqlalchemy`, `asyncpg`, `alembic`. Wire `db.py` (engine, session dependency).
3. **Alembic**: init async template, configure `alembic.ini` + `env.py` to read `Settings.database_url`, first empty migration, `upgrade head` works.
4. **pytest setup**: `pytest`, `pytest-asyncio`, `httpx` dev deps; `conftest.py` with app + test-db fixtures; the health test now runs through the real fixture stack.
5. **CI**: GitHub Actions workflow (backend job as in §9). Push and confirm green.

Then Phase 1 (users + auth) following §5, one vertical slice at a time: user model + roles → email provider → request-code/verify/logout → onboarding invitations → audit events.

## 11. Deliberately not doing (for now)

Anti-over-engineering list — revisit only when a real need appears:

- No repository/unit-of-work pattern, no CQRS, no event bus.
- No background job runner (tenancy expiry is checked at request time; log retention can be a manual/cron SQL cleanup).
- No JWT/OAuth — first-party cookie sessions only.
- No multi-tenancy, no horizontal scaling concerns (a few hundred users).
- No real email provider until the console mock stops being enough.
- No payment gateway — billing stays view-only with manual mark-as-paid.
