FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fonts-noto-cjk libreoffice-writer poppler-utils tesseract-ocr tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.12.1 \
    && useradd --create-home --uid 10001 app

WORKDIR /app
COPY --chown=app:app services/api/pyproject.toml services/api/uv.lock ./
RUN uv sync --frozen --no-dev
COPY --chown=app:app services/api/app ./app
COPY --chown=app:app services/api/migrations ./migrations
COPY --chown=app:app services/api/alembic.ini ./alembic.ini

USER app
CMD ["python", "-m", "app.entrypoints.api"]
