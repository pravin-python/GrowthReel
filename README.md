# GrowthReel

A three-service project:

| Service | Path | Stack | Purpose |
|---|---|---|---|
| **Backend** | [`backend/`](backend/README.md) | Django 5.2 + Tailwind CSS v4.3.3 | Public marketing site at `growthreel.com`: blog, session-based login, and the Django admin, which doubles as the internal CRM UI (Leads/Clients). Owns the one source of truth for identity (`apps.users.models.User`). |
| **API** | [`api/README.md`](api/README.md) | FastAPI + JWT | Backs the dashboard at `app.growthreel.com`. Imports the Django backend's ORM **in-process** (`django.setup()`), so it reuses the exact same models and database — no HTTP calls between the two Python services. |
| **Frontend app** | [`frontend-app/README.md`](frontend-app/README.md) | React 19 + Vite + TypeScript + Tailwind v4 | The SPA dashboard at `app.growthreel.com` itself. Talks only to the FastAPI service. |

Each service was built and verified independently (see its own README's
"Verification" section); this document covers how they fit together, and how
to run all three at once.

## How login works end-to-end (the SSO handoff)

1. A user logs in at `growthreel.com/accounts/login/` — an ordinary Django
   session login, rendered with Tailwind.
2. On success, Django redirects the browser to
   `{APP_FRONTEND_URL}/auth/callback?token=<bridge_jwt>` instead of a Django
   page. `<bridge_jwt>` is a 60-second, single-use HS256 JWT minted by
   `apps.users.services.issue_bridge_token`, signed with `SHARED_JWT_SECRET`
   — the one secret both the Django backend and the FastAPI service must
   share byte-for-byte.
3. The React app's `/auth/callback` route calls
   `POST /api/v1/auth/exchange {"bridge_token": "..."}` on the FastAPI
   service. FastAPI verifies the bridge token's signature/expiry/type,
   (in production) checks it hasn't been replayed via Redis, looks the user
   up through the **shared Django ORM**, and mints its own access token
   (returned in the response body, kept in memory by React) and refresh
   token (set as an httpOnly cookie).
4. From then on, the React app calls `/api/v1/...` with
   `Authorization: Bearer <access_token>`, silently refreshing via the
   cookie-based `/api/v1/auth/refresh` endpoint when needed.

Full details, exact JWT claims, and the single-use/replay story are in
[`backend/README.md`](backend/README.md) ("Contract for the FastAPI
service") and [`api/README.md`](api/README.md).

## Security hardening summary

The two backend services deliberately apply **different** CSPs, for a
documented reason — see each middleware's own docstring:

- **FastAPI** (`api/app/core/middleware.py`, `ws_security_headers.py`) is
  pure JSON/WebSocket, so it uses the literal, maximally strict policy as
  originally specified: `Content-Security-Policy: default-src 'none';
  frame-ancestors 'none'; base-uri 'none'`, plus
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer`, `Cache-Control: no-store`,
  `X-XSS-Protection: 1; mode=block`, and HSTS in production. The same set is
  applied to the WebSocket 101 handshake response.
- **Django** (`backend/apps/core/middleware.py`) renders real HTML/CSS/JS
  (the Tailwind site, the admin), so a blanket `'none'` would break it. It
  keeps `frame-ancestors 'none'` and relaxes the rest to `'self'`.

**VAPT fixes implemented**, per the original brief:
- **Server banner** — `api/app/core/uvicorn_worker.py` runs uvicorn with
  `server_header=False` (confirmed via `uvicorn --help`: the CLI flag is
  `--no-server-header`). Both nginx configs (`frontend-app/nginx.conf`,
  `deploy/nginx/edge.conf`) set `server_tokens off;`.
- **Internal IP/hostname leak** — `GET /api/v1/health` is public and returns
  only `{"status": "ok"}`; `GET /api/v1/health/detailed` requires auth and
  only ever returns booleans/strings, never a hostname/IP/path/traceback.
- **Verbose errors** — a global FastAPI exception handler returns a generic
  `500 {"detail": "Internal server error", "request_id": "..."}` for any
  unhandled exception; the full exception is logged server-side only.
- **Cookies** — the `refresh_token` cookie is `HttpOnly`, `SameSite=Lax`, and
  `Secure` whenever the service runs in production mode.
- **Request ID / session ID** — every HTTP response from both backends
  carries `X-Request-ID` (propagated from an incoming request or generated
  fresh); every WebSocket connection gets its own `session_id`, sent as the
  first message.

## Running everything together (docker-compose)

```bash
cp backend/.env.example backend/.env
cp api/.env.example api/.env
# Edit both files and set the SAME value for SHARED_JWT_SECRET in each —
# this is required, not optional (see "How login works" above).

docker compose up --build
```

This starts Postgres, Redis, the Django backend (gunicorn + migrations),
a Celery worker, the FastAPI service, the built React app (served by its own
nginx), and a root `edge` nginx that routes by hostname:

- `http://growthreel.localhost/` → the Django site
- `http://app.growthreel.localhost/` → the React app (which itself proxies
  `/api/` to the FastAPI service)

`*.localhost` resolves to `127.0.0.1` automatically on most modern
OSes/browsers; if yours doesn't, add both hostnames to your hosts file
pointing at `127.0.0.1`.

**Not covered by this compose file:** TLS termination (it's plain HTTP,
local-dev only — see `DJANGO_FORCE_HTTPS` and the `ENV` var on the `api`
service for why), and a production-grade Postgres/Redis setup (single
container, no replication/backups). See each service's own README for
production deployment notes.

**Known limitation of this delivery:** this compose stack, and the
Dockerfiles it builds, were written to the same spec as everything else but
**could not be executed here** — no Docker CLI is available in the sandbox
this project was built in. Each service's own code *was* run and verified
directly (see each README's "Verification" section); the compose wiring
itself (service names, ports, env var overrides) has been reviewed for
consistency (e.g. the `api` port mismatch between `frontend-app/nginx.conf`
and `api/Dockerfile` that the two services' independent builders flagged was
found and fixed — both now agree on `8001`) but has not had an actual
`docker compose up` run against it. Please run it and report back anything
that doesn't come up cleanly.

## Local development without Docker

Each service has its own, independently runnable local-dev setup — see:

- [`backend/README.md`](backend/README.md) "Setup from scratch"
- [`api/README.md`](api/README.md) "Setup" section
- [`frontend-app/README.md`](frontend-app/README.md) "Setup" section

**Note on `backend/config/settings/local.py`:** at the time this project was
scaffolded, local dev used SQLite with no external dependencies. That file
has since been changed (outside of this scaffolding work) to require a real
local Postgres instance via `DB_ENGINE`/`DB_NAME`/`DB_USER`/`DB_PASSWORD`/
`DB_HOST`/`DB_PORT` env vars, with no defaults for name/user/password — so
`manage.py runserver` against `config.settings.local` now needs a reachable
Postgres (e.g. `docker compose up postgres` from this root, or your own
install) that it didn't need before. `config.settings.production` was then
updated (as part of this later integration pass) to use the exact same
discrete `DB_*` variables plus a `DB_SSLMODE` option, instead of its
original single `DATABASE_URL` value — one connection-config pattern for
both environments now, documented in `backend/.env.example`. This doesn't
affect `config.settings.testing` (used by the backend's own pytest suite),
which is untouched and still uses an isolated in-memory SQLite DB. The one
remaining inconsistency is that `backend/README.md`'s "Verification
performed" section still describes the
original SQLite-based verification run — that section is a historical
record of what was actually executed and wasn't rewritten to match, so it
no longer matches `local.py`'s current behavior; flagging it here rather
than editing a section that documents something that genuinely happened.

## CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs three
independent pipelines (backend, api, frontend), each with lint, test, and a
security-audit job (`bandit` + `pip-audit` for the Python services, `npm
audit` for the frontend). Backend and API tests both run against SQLite
(`config.settings.testing` / a disposable per-run SQLite file — see
`api/tests/conftest.py`), so CI needs no Postgres/Redis service containers.

**Automated test coverage added as part of this integration pass** (neither
service had an automated suite before this): `backend/apps/*/tests.py`
(pytest-django, 22 tests covering the bridge-JWT contract, CRM/blog
services, and the security headers/request-id middleware) and
`api/tests/` (plain pytest + FastAPI's `TestClient`, 25 tests covering the
full exchange→refresh→logout lifecycle against a real Django-ORM-backed
SQLite DB, leads/posts endpoints calling the real Django service functions,
and the WebSocket handshake). Both suites currently pass in full.

**Not run in this environment:** `pre-commit` itself (it needs to clone
hook repos from GitHub, network access this sandbox didn't reliably have) —
the config at [`.pre-commit-config.yaml`](.pre-commit-config.yaml) is
written and scopes each tool (ruff/black/mypy/bandit) to the right service
via `files:`, but hasn't been run end-to-end. `docker compose up` likewise
(see above).

## Repository layout

```
GrowthReel/
  backend/            Django: growthreel.com (marketing site, blog, admin/CRM)
  api/                FastAPI: app.growthreel.com's backend (shared Django ORM, JWT)
  frontend-app/        React: app.growthreel.com's UI
  deploy/nginx/edge.conf   Local docker-compose routing by hostname
  docker-compose.yml   All of the above + Postgres + Redis + Celery, wired together
  .github/workflows/ci.yml
  .pre-commit-config.yaml
```
