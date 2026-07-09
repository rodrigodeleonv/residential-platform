# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Residential Platform: a condominium/residential management SaaS (single deployment per condominium, not multi-tenant, ~400 users). Monorepo:

- `apps/api` — Python 3.14+ / FastAPI backend, managed with `uv`. PostgreSQL is the database.
- `apps/web` — React + TypeScript frontend (not scaffolded yet).
- `docs/development-plan.md` — the development plan and architecture decisions. Read it before starting feature work.
- `requeriments.md` — business requirements (in Spanish). **Gitignored on purpose and never tracked. Always ask the user for permission before modifying it.**

## Working agreements

- All code, comments, docs, commit messages, and identifiers in English (requirements doc stays in Spanish).
- TypeScript whenever possible on the frontend — no plain JS.
- Do not add Claude as co-author in git commits.
- Avoid over-engineering; prefer the simple design. Scale target is small (~400 users).
- All API endpoints go under the `/api/v0/` prefix (version bumps only on breaking changes).
- Every feature is completed together with tests that validate it (pytest on the backend; Vitest/Playwright on the frontend once it exists).

## Commands (backend, run from `apps/api/`)

- `uv sync` — install/sync dependencies
- `uv run ruff check .` / `uv run ruff format .` — lint / format
- `uv run pyright` — type check
- `uv run pytest` — tests (pytest is the chosen test runner; not yet added)

Add dependencies with `uv add <pkg>` (or `uv add --dev <pkg>`), never by editing `pyproject.toml` by hand.
