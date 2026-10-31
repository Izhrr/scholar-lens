FROM python:3.12.16-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /bin/uv

WORKDIR /app

# Dependencies first so code edits do not reinstall them.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# UID 1000 matches the usual Linux desktop user, so the bind-mounted PDF folder stays writable.
RUN useradd --uid 1000 --create-home scholarlens \
    && mkdir -p /app/data/papers /app/models \
    && chown -R scholarlens /app/data /app/models
USER scholarlens

EXPOSE 8000

# One worker on purpose: the BM25 index and ingestion jobs live in this process.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
