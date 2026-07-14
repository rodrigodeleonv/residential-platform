# Residential Platform

Management platform for a single residential condominium (a few hundred users): units & occupancy, vehicles & parking, visitor management (gatehouse), common-area reservations, and billing view. Not multi-tenant — one deployment per condominium.

## Repository layout

| Path | Description |
|---|---|
| `apps/api` | Backend — Python 3.14, FastAPI, PostgreSQL, managed with [uv](https://docs.astral.sh/uv/) |
| `apps/web` | Frontend — React + TypeScript SPA, built with Vite, managed with [pnpm](https://pnpm.io/) |
| `docs/` | Development plan and implementation guide |

## Prerequisites

- [Docker](https://www.docker.com/) — runs PostgreSQL and the app containers. Infrastructure always runs in Docker; nothing is installed on the host OS.
- [uv](https://docs.astral.sh/uv/) — Python toolchain for backend development.
- Node.js LTS (e.g. via [nvm](https://github.com/nvm-sh/nvm)) and [pnpm](https://pnpm.io/) (`npm install -g pnpm`) — frontend development. pnpm is deliberate: it blocks dependency install scripts and quarantines just-published versions (see `apps/web/pnpm-workspace.yaml`), the main defenses against npm supply-chain attacks.

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

For the frontend, in another terminal:

```bash
cd apps/web
pnpm install
pnpm dev
```

The app is served at `http://localhost:5173` and proxies `/api` to the local API.

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

Run from `apps/web/`:

```bash
pnpm test                  # tests (Vitest)
pnpm lint                  # lint (eslint)
pnpm typecheck             # type check (tsc)
```

All of these must pass before committing.

## Documentation

- [`docs/development-plan.md`](docs/development-plan.md) — business rules, architecture decisions, and phased roadmap.
- [`docs/implementation-guide.md`](docs/implementation-guide.md) — code structure, conventions, and how-to details.
- [`docs/deployment.md`](docs/deployment.md) — production deployment (`docker-compose.prod.yml`, TLS, backups).
