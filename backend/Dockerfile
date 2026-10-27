# syntax=docker/dockerfile:1

# ---- Builder stage: install Python deps + collect static assets ----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements/ requirements/
RUN pip install -r requirements/production.txt

COPY . .

# Dummy settings for collectstatic only: a real SECRET_KEY/DB connection
# isn't needed to collect static files, but DJANGO_SETTINGS_MODULE and the
# required DB_* vars must resolve (production.py has no defaults for them).
RUN DJANGO_SETTINGS_MODULE=config.settings.production \
    DJANGO_SECRET_KEY=build-time-only-not-used-at-runtime \
    DB_NAME=placeholder \
    DB_USER=placeholder \
    DB_PASSWORD=placeholder \
    REDIS_URL=redis://localhost:6379/0 \
    python manage.py collectstatic --noinput

# ---- Final stage: minimal runtime image, non-root user --------------------
FROM python:3.12-slim AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 growthreel \
    && useradd --uid 1000 --gid growthreel --shell /bin/bash --create-home growthreel

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

RUN chown -R growthreel:growthreel /app

USER growthreel

EXPOSE 8000

# Shell form (not exec-form array) so $PORT expands at container start — Cloud
# Run injects PORT dynamically; docker-compose/local runs fall back to 8000.
CMD gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3
