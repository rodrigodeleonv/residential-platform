# Residential Platform

Management platform for a single residential condominium (a few hundred users): units & occupancy, vehicles & parking, visitor management (gatehouse), common-area reservations, and billing view. Not multi-tenant — one deployment per condominium.

## Repository layout

| Path | Description |
|---|---|
| `apps/api` | Backend — Python 3.14, FastAPI, PostgreSQL, managed with [uv](https://docs.astral.sh/uv/) |
| `apps/web` | Frontend — React + TypeScript (not scaffolded yet) |
| `docs/` | Development plan and implementation guide |

## Prerequisites

- [Docker](https://www.docker.com/) — runs PostgreSQL and the app containers. Infrastructure always runs in Docker; nothing is installed on the host OS.
- [uv](https://docs.astral.sh/uv/) — Python toolchain for backend development.
- Node.js — only needed once frontend work starts (Phase 4).

## Quickstart (backend development)

```bash
# 1. Start PostgreSQL
docker compose up -d postgres

# 2. Install dependencies and apply migrations
cd apps/api
uv sync
uv run alembic upgrade head

# 3. Run the API with hot reload
uv run uvicorn app.main:app --reload
```

The API is served at `http://localhost:8000` (endpoints under `/api/v0/`, interactive docs at `/docs`).

To run the full stack in containers instead:

```bash
docker compose up --build
```

## Development

Run from `apps/api/`:

```bash
uv run pytest              # tests (requires the compose postgres running)
uv run ruff check .        # lint
uv run ruff format .       # format
uv run pyright             # type check
```

All of these must pass before committing.

## Documentation

- [`docs/development-plan.md`](docs/development-plan.md) — business rules, architecture decisions, and phased roadmap.
- [`docs/implementation-guide.md`](docs/implementation-guide.md) — code structure, conventions, and how-to details.
- [`docs/deployment.md`](docs/deployment.md) — production deployment (`docker-compose.prod.yml`, TLS, backups).
