# syntax=docker/dockerfile:1

# ---- Builder stage: install Python deps -----------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements/ requirements/
RUN pip install -r requirements/production.txt

# ---- Final stage: minimal runtime image, non-root user ---------------------
FROM python:3.12-slim AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN groupadd --gid 1000 growthreel \
    && useradd --uid 1000 --gid growthreel --shell /bin/bash --create-home growthreel

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

# This image only has `api/`'s own source baked in. The sibling `backend/`
# Django project (whose ORM this service calls directly via django.setup())
# must be mounted/copied into the container at the path configured by
# BACKEND_DIR (see .env.example) by whatever composes the two images
# together — that wiring is explicitly owned by the root docker-compose/CI
# pass per this project's brief, not by this Dockerfile. A docker-compose
# setup will typically bind-mount ../backend to /backend and set
# BACKEND_DIR=/backend here.

RUN chown -R growthreel:growthreel /app

USER growthreel

EXPOSE 8001

# Runs through this project's own uvicorn_worker entrypoint (see
# app/core/uvicorn_worker.py) rather than invoking `uvicorn` directly, so the
# Server-header-suppression (and any future worker-level) configuration
# lives in one place in source control instead of being duplicated here as
# CLI flags that could drift from it.
CMD ["python", "-m", "app.core.uvicorn_worker"]
