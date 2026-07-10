# Build stage: resolve and install dependencies with uv into a self-contained venv.
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Install dependencies first so this layer is cached until the lockfile changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY . .

# Runtime stage: slim image, non-root user, only the app and its venv.
FROM python:3.14-slim-bookworm

RUN useradd --create-home appuser
WORKDIR /app
COPY --from=builder --chown=appuser:appuser /app /app
USER appuser
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
