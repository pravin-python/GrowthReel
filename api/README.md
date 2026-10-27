# GrowthReel — FastAPI Service (`api/`)

This is the **API for `app.growthreel.com`**, one of three services in the
GrowthReel project:

- **`backend/`** (sibling directory) — Django. Server-rendered marketing
  site, blog, Django admin (used as the CRM UI), session-based login, and
  the identity/user model everything else depends on.
- **`api/`** (this directory) — FastAPI service for `app.growthreel.com`.
  Imports `backend/`'s project and calls `django.setup()` to reuse the
  Django ORM models and service functions directly, in-process, against the
  exact same database — **no HTTP calls to Django, ever**.
- **`frontend-app/`** (sibling directory, built separately) — React SPA for
  `app.growthreel.com`. Talks only to this service, at `/api/v1/...`.

A root-level `docker-compose` / CI setup wiring all three together is owned
by a later pass and is intentionally **not** included here (see "Notes for
the root integrator" at the bottom).

## The core trick: Django ORM reused in-process

`app/core/django_orm.py::setup_django()` inserts `backend/`'s absolute path
onto `sys.path`, sets `DJANGO_SETTINGS_MODULE`, and calls `django.setup()`
**once**, from this app's `lifespan` hook (`app/main.py`), before uvicorn
starts accepting requests. After that, any route can do
`from apps.crm.models import Lead` or
`from apps.crm.services import change_lead_status` and get the real Django
ORM/business logic, talking to the same SQLite file (`backend/db.sqlite3`
locally) or Postgres (production) that Django itself uses.

Every route lazy-imports its Django models/services **inside the function
body**, not at module level — this is a deliberate extra safety margin so
that importing `app/main.py` (and the routers it includes) can never
accidentally touch Django before `setup_django()` has run, regardless of
import order.

Because Django's ORM is sync and FastAPI/Starlette is async, **every** ORM
call goes through `asgiref.sync_to_async` (e.g.
`await sync_to_async(User.objects.get)(pk=claims["sub"])`), or wraps a small
sync helper function with `sync_to_async` when several ORM calls need to
happen together (see `app/api/v1/routes/leads.py::_patch_lead_sync`).

## Directory layout

```
api/
  requirements/{base,local,production,testing}.txt
  pyproject.toml              [tool.ruff]/[tool.black]/[tool.mypy] config only
  .env.example / .env (gitignored) / .gitignore
  .pre-commit-config.yaml
  Dockerfile                  multi-stage, non-root user, EXPOSE 8001
  README.md                   this file
  scripts/                    throwaway dev/verification scripts (not part of the shipped app)
    sanity_check.py           django.setup() + User.objects.count() smoke test
    verify_e2e.py             mints a real bridge token via the ORM, seeds a Lead/Post if needed
    verify_ws.py              WS client: connects, checks handshake headers + session.init
    verify_ws_bad_token.py    WS client: confirms an invalid token is rejected before accept
  app/
    main.py                   FastAPI() app, lifespan -> setup_django(), middleware, routers, exception handlers
    core/
      config.py                pydantic-settings Settings
      django_orm.py             setup_django() (idempotent)
      security.py               create_access_token/create_refresh_token/decode_token/verify_bridge_token
      middleware.py             RequestIDMiddleware, SecurityHeadersMiddleware, apply_security_headers()
      ws_security_headers.py    header list applied to the WS 101 response
      uvicorn_worker.py         run() -> uvicorn.run(..., server_header=False)
      redis_client.py           bridge-jti replay check + refresh-jti revocation, with graceful fallback
    api/
      v1/
        router.py                aggregates all v1 routers under "/api/v1"
        deps.py                  get_current_user
        schemas.py               pydantic request/response models
        routes/
          auth.py                  POST /auth/exchange, /auth/refresh, /auth/logout, GET /auth/me
          health.py                GET /health, GET /health/detailed
          leads.py                 GET /leads, PATCH /leads/{id}
          posts.py                 GET /posts
        ws/
          notifications.py         WS /ws/notifications?token=...
```

## Dependency management: why `requirements/*.txt` + `pyproject.toml`

Same situation as `backend/`: `uv` has no matching distribution on this
machine's pip index, so installation uses plain `pip` against
`requirements/{base,local,production,testing}.txt`. `pyproject.toml` holds
only metadata + tool config (`[tool.ruff]`/`[tool.black]`/`[tool.mypy]`).

**`requirements/base.txt` pins more than just "Django + FastAPI".** Beyond
`Django==5.2.6`, `django-environ==0.11.2`, and `PyJWT==2.9.0` (pinned to
match `backend/requirements/base.txt` exactly, to avoid ORM/migration drift
between the two processes), it also pins `celery==5.4.0`,
`django-cors-headers==4.4.0`, `djangorestframework==3.15.2`, and
`Pillow==10.4.0` — **none of which this service's own code uses**. This was
discovered during verification, not assumed up front: `django.setup()`
imports `backend/config/__init__.py` (which imports `backend/config/celery.py`,
which does `from celery import Celery` at module level) and populates
`INSTALLED_APPS` (which lists `"corsheaders"` and `"rest_framework"`, and
`apps.blog.models.Post.cover_image` is an `ImageField`, which touches
Pillow). Without all four installed, `django.setup()` fails with
`ModuleNotFoundError` even though this service never creates a Celery app,
never uses DRF, and never handles image uploads. Each is commented in
`requirements/base.txt` explaining why it's there.

## Setup from scratch (Windows / Git Bash)

```bash
cd E:\Django_project\practice\GrowthReel\api

# 1. Create a project-local virtualenv with Python 3.12.
"C:\Users\pc050607\AppData\Local\Programs\Python\Python312\python.exe" -m venv .venv

# 2. Install dependencies.
.venv/Scripts/python.exe -m pip install --upgrade pip
.venv/Scripts/python.exe -m pip install -r requirements/testing.txt   # or local.txt for a non-test install

# 3. Create your local .env from the template.
cp .env.example .env
#   SHARED_JWT_SECRET and APP_FRONTEND_URL MUST match backend/.env's values
#   byte-for-byte — see "Environment variables" below.

# 4. Make sure backend/ is set up and migrated (SQLite, no Postgres/Redis
#    required for local dev) — see backend/README.md if it isn't yet.

# 5. Run the dev server.
.venv/Scripts/python.exe -m app.core.uvicorn_worker
#   or directly: .venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8001 --no-server-header
#   visit http://localhost:8001/api/v1/health
```

### Running tests

```bash
.venv/Scripts/python.exe -m pip install -r requirements/testing.txt
.venv/Scripts/python.exe -m pytest
```

(No `tests/` suite is included in this pass — `requirements/testing.txt`
and the `scripts/verify_*.py` scripts are the testing/verification tooling
actually exercised; see "Verification performed" below for what they proved
against the real backend. A `pytest` suite using `httpx.AsyncClient` against
`app.main.app`, with `apps.users.services.issue_bridge_token` used to mint
real bridge tokens the same way `scripts/verify_e2e.py` does, is the natural
next addition.)

### Pre-commit hooks

```bash
.venv/Scripts/python.exe -m pip install pre-commit
.venv/Scripts/python.exe -m pre_commit install
```

## Environment variables

See `.env.example` for the full list. The ones that **must match
`backend/.env` byte-for-byte**:

| variable            | shared? | purpose                                                              |
|---------------------|---------|------------------------------------------------------------------------|
| `SHARED_JWT_SECRET`  | yes     | HS256 signing secret for the bridge JWT (and, here, this service's own access/refresh JWTs too — see `app/core/security.py`). |
| `APP_FRONTEND_URL`   | yes     | Base URL of the React SPA; Django builds the post-login redirect to it. |
| `REDIS_URL`          | yes     | Shared cache/broker; where the authoritative bridge-jti replay check lives in production. |

**Confirmed for this pass:** `api/.env`'s `SHARED_JWT_SECRET` is set to the
*exact* value already in `backend/.env`
(`local-dev-shared-jwt-secret-please-rotate-before-any-real-use-abcdefgh`) —
copied, not reinvented — which is what made the real end-to-end bridge-token
verification below possible at all (a mismatched secret would make every
`/auth/exchange` call fail signature verification). `api/.env` is covered by
`api/.gitignore`; only `api/.env.example` (placeholder value) is meant to be
committed.

`BACKEND_DIR` defaults to `../backend` relative to this directory, resolved
to an absolute path, and is also explicit in `.env`/`.env.example` for
clarity and for container deployments where the relative-path assumption
won't hold (see "Notes for the root integrator").

## Auth design decisions

- **One shared secret, three token kinds.** `bridge` (minted by Django,
  60s TTL), `access` (minted here, 900s/15min TTL), and `refresh` (minted
  here, 1,209,600s/14-day TTL) are all HS256 JWTs signed with the same
  `SHARED_JWT_SECRET`. Using one key for our own tokens too (rather than a
  second FastAPI-only secret) is a deliberate simplification — nothing
  about our own access/refresh tokens is shared cross-service except the
  bridge token, so a second secret would just be one more value to keep in
  sync for no real security benefit.
- **Refresh token rotation.** `POST /auth/refresh` both mints a new access
  token *and* rotates the refresh cookie (revoking the old refresh `jti` and
  setting a new one), rather than reusing the same refresh token across
  calls. This bounds how long a stolen refresh token stays useful to
  roughly one refresh cycle, at the cost of one extra Redis write per
  refresh in production. Documented here per the task's "your call, document
  whichever you pick."
- **Logout best-effort revoke.** `POST /auth/logout` decodes the refresh
  cookie (if present, ignoring any decode failure) and records its `jti` in
  Redis as revoked for its remaining lifetime, then always clears the
  cookie and returns `204` — a Redis outage never prevents logout from
  working from the client's point of view.
- **Redis is genuinely optional for local dev.** `app/core/redis_client.py`
  implements `consume_bridge_jti` (used by `/auth/exchange`) and
  `is_refresh_jti_revoked`/`revoke_refresh_jti` (used by `/auth/refresh` and
  `/auth/logout`). In `ENV != "production"`, all three skip the Redis
  round-trip entirely and the bridge/refresh JWTs' own signature + `exp` are
  the only enforcement — exactly mirroring `backend/README.md`'s reviewer
  note that local Django's `LocMemCache` is invisible to a separate FastAPI
  process anyway. In production, a Redis **connection error** is caught and
  logged, then **fails open** (treated as "not revoked"/"not replayed") so
  a Redis outage degrades to "replay protection temporarily unavailable"
  rather than "nobody can log in" — the JWT signature and expiry are still
  fully enforced regardless. This tradeoff is documented in the docstrings
  of each function in `redis_client.py`.
- **Cookie flags.** `refresh_token` is always `HttpOnly` and
  `SameSite=Lax`, scoped to `Path=/api/v1/auth` (so it's never sent to
  `/leads`, `/posts`, etc.), with `Max-Age` = `REFRESH_TOKEN_TTL_SECONDS`.
  `Secure` is conditional on `ENV=="production"` — a `Secure` cookie is
  silently dropped by the browser over plain `http://localhost`, which
  would make local login impossible, so it's only set once real HTTPS is in
  play.
- **WebSocket auth via query param.** Browsers can't set custom headers on
  a WS handshake, so `?token=<access_token>` is the one place in this
  service a bearer credential travels outside a header. An invalid/missing
  token is rejected with `websocket.close(code=4401)` called **before**
  `accept()` — in practice (confirmed live, see Verification step 9b) this
  makes the ASGI server refuse the handshake outright with an HTTP `403`,
  since there's no established WS connection yet for a close *frame*
  carrying code `4401` to travel over. This is standard, correct ASGI
  behavior for a pre-accept close and is arguably cleaner than accepting
  and immediately dropping the connection.

## Security headers

Applied via `SecurityHeadersMiddleware` (`app/core/middleware.py`) to every
ordinary HTTP response, and the WebSocket-handshake equivalent via
`app/core/ws_security_headers.py`:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Cache-Control: no-store
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload   (ENV=="production" only)
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'
```

Unlike `backend/`'s `SecurityHeadersMiddleware` (which has to relax its CSP
because it renders real HTML/CSS/JS), this service is pure JSON/WebSocket
with nothing to render, so the original spec's literal, maximally strict
policy is used **as-is, unmodified**.

`X-Request-ID` is added to every HTTP response (generated if the client
didn't send one, echoed back if they did — `RequestIDMiddleware`), and a
per-connection `session_id` (a fresh uuid4, sent as the first WS message:
`{"type":"session.init","session_id":"..."}`) for every WebSocket client.

**Gap found and fixed during verification:** `@app.exception_handler(Exception)`
is backed by Starlette's `ServerErrorMiddleware`, which wraps **outside**
every middleware added via `app.add_middleware(...)` — so a response built
by that handler (any unhandled exception → generic 500) never passes back
through `SecurityHeadersMiddleware`/`RequestIDMiddleware` the normal way.
The first working version of this service had a genuine bug here: the 500
response was missing every security header. Fixed by extracting
`apply_security_headers()` as a standalone function (`app/core/middleware.py`)
called both by the middleware's `dispatch()` *and* directly from
`app/main.py::unhandled_exception_handler`, which also sets `X-Request-ID`
by hand on that response. Verified live after the fix (see Verification
step 10).

## VAPT fixes implemented

1. **#14 Server banner.** `app/core/uvicorn_worker.py` calls
   `uvicorn.run(..., server_header=False)`. **Verified, not just
   configured:** `.venv/Scripts/python.exe -m uvicorn --help` was run
   against this project's own venv and lists the real CLI-equivalent flag:

   ```
   --server-header / --no-server-header   Enable/Disable default Server header.
   ```

   So the CLI flag (e.g. for the Dockerfile/README of a future pass that
   invokes `uvicorn` directly instead of through `uvicorn_worker.py`) is
   **`--no-server-header`**. `curl -i http://localhost:8001/api/v1/health`
   against the live dev server confirmed no `Server` header at all in the
   response (only `date`, `content-type`, `content-length`, and this
   service's own headers).

2. **#16 Internal IP/hostname leak.** `GET /api/v1/health` is public and
   returns exactly `{"status": "ok"}`, nothing else. `GET /api/v1/health/detailed`
   requires auth (`get_current_user`) and returns only
   `{"database": "ok"|"unavailable", "cache": "ok"|"unavailable", "version": "..."}`
   — never a hostname, internal IP, file path, or stack trace. The CSP and
   every other header never reference an internal hostname.

3. **#13 Verbose errors.** `app/main.py::unhandled_exception_handler`
   (`@app.exception_handler(Exception)`) logs the full exception
   server-side (with the request id, via Python logging) and always
   returns `500 {"detail": "Internal server error", "request_id": "..."}`
   — applied **unconditionally**, not gated on `ENV=="production"`, so
   local dev sees the exact same response shape production does (the full
   traceback still goes to the server log either way, so nothing is lost
   for local debugging — this was the simpler, documented choice the task
   left to our judgment). Every error response from this service (401, 400,
   404, 500, FastAPI's own 422 validation errors) is valid, parseable JSON
   with a `detail` key — so `frontend-app/src/lib/safeJson.ts`'s
   `response.text()` → `JSON.parse()` wrapper (which the actual helper
   lives in, over in `frontend-app/`, not here) will always succeed on a
   non-empty body.

4. **Cookies.** Covered above under "Auth design decisions".

5. **Request ID / session ID.** Covered above under "Security headers".

## Endpoint contract

Matches `backend/README.md`'s "Contract for the FastAPI service" and was
also cross-checked line-by-line against `frontend-app/src/lib/types.ts`,
`apiClient.ts`, `authApi.ts`, and `hooks/useNotifications.ts` (the React app
was already built when this service was written — see "Notes for the React
engineer" below for the one place this mattered).

| Method & path | Auth | Request | Success | Errors |
|---|---|---|---|---|
| `POST /api/v1/auth/exchange` | none | `{"bridge_token": "<jwt>"}` | `200 {"access_token","token_type":"bearer","expires_in":900}` + `Set-Cookie: refresh_token=...` | `401` bad sig / expired / wrong `typ` / failed replay check |
| `POST /api/v1/auth/refresh` | refresh cookie | — | `200` same shape as exchange; rotates the refresh cookie | `401` cookie missing/invalid/expired/revoked |
| `POST /api/v1/auth/logout` | refresh cookie (optional) | — | `204`, clears cookie | — |
| `GET /api/v1/auth/me` | Bearer | — | `200 {"id","email","first_name","last_name","role"}` | `401` |
| `GET /api/v1/health` | none | — | `200 {"status":"ok"}` | — |
| `GET /api/v1/health/detailed` | Bearer | — | `200 {"database","cache","version"}` | `401` |
| `GET /api/v1/leads` | Bearer | `?status=` optional | `200 [LeadOut, ...]` | `401`, `400` invalid status |
| `PATCH /api/v1/leads/{id}` | Bearer | `{"status": "..."}` | `200 LeadOut` | `401`, `400` invalid status, `404` |
| `GET /api/v1/posts` | Bearer | — | `200 [PostOut, ...]` | `401` |
| `WS /api/v1/ws/notifications?token=` | access token (query param) | — | `session.init` then periodic `notification` | handshake rejected (HTTP 403) if token invalid/missing |

**`LeadOut`:** `{"id","name","email","phone","company","status","source","owner_id","created_at"}`
**`PostOut`:** `{"id","title","slug","status","published_at","author_email"}`

### One place this service's shape differs from a literal reading of the contract — and why that's correct

`backend/README.md`'s contract table writes `Lead.id`/`Post.id` the same way
it writes every other field (`"id": "..."`), which could be read either way
given `Lead`/`Post`/`Client`/`Category` all use Django's default
`BigAutoField` (an integer), not a UUID like `User.id`. **This service
serializes every `id` field as a `str`, including `Lead.id` and `Post.id`**
(`str(lead.pk)`, `str(post.pk)`) — confirmed correct, not guessed, by
reading `frontend-app/src/lib/types.ts`, which was already written against
this contract and explicitly declares `id: string` on both `Lead` and
`Post`. Serializing them as `int` instead would have broken the already-built
React app the first time it rendered a lead/post id. `owner_id` (a `User`
UUID FK) is a `str | null` either way.

## Verification performed

All of the following were run against `config.settings.local` (SQLite, no
Postgres/Redis required) using this project's own `.venv`, against the
**real** `backend/db.sqlite3` and real `backend/` code:

1. **`django.setup()` from a separate process/venv** — `scripts/sanity_check.py`
   (`setup_django()` then `User.objects.count()`) ran successfully:
   `User.objects.count() = 1`. This is what surfaced the `celery`/
   `corsheaders`/`rest_framework`/`Pillow` transitive-dependency gap
   described above under "Dependency management" — the script failed three
   times in a row with different `ModuleNotFoundError`s before all four
   were identified and pinned.
2. **Dev server startup** — `python -m app.core.uvicorn_worker` started
   cleanly: `Application startup complete` / `Uvicorn running on
   http://0.0.0.0:8001`.
3. **`curl -i http://localhost:8001/api/v1/health`** — `200`,
   `{"status":"ok"}`, all six security headers present, `X-Request-ID`
   present, **no `Server` header**.
4. **Real end-to-end bridge flow** — `scripts/verify_e2e.py` used this
   venv's own `django.setup()` access to fetch the one real `User` row
   (`admin@growthreel.com`), create a `Lead` and a `Post` via the ORM (none
   existed yet), and call the real `apps.users.services.issue_bridge_token(user)`
   to mint a genuine bridge JWT exactly as the real Django login view
   would. That token was `POST`ed to the running `/api/v1/auth/exchange`:
   `200` with an `access_token` and a `Set-Cookie: refresh_token=...`
   header, confirmed via `curl -i`.
5. **`GET /auth/me`** with that access token → `200` with the exact right
   user (`admin@growthreel.com`, `role: admin`, matching UUID).
6. **`POST /auth/refresh`** with the cookie from step 4 (`curl -b`) → `200`
   with a new `access_token` and a rotated `Set-Cookie`.
7. **Leads round-trip** — `GET /api/v1/leads` returned the seeded lead,
   correctly shaped; `PATCH /api/v1/leads/1 {"status":"qualified"}`
   returned `200` with the updated status; a follow-up `GET` confirmed the
   change actually persisted in the database — proving
   `apps.crm.services.change_lead_status` was genuinely called, not
   reimplemented. `?status=bogus` correctly returned `400`.
8. **`GET /api/v1/posts`** → `200` with the seeded post, correctly shaped
   (`author_email` resolved via `select_related("author")`).
9. **WebSocket** — `scripts/verify_ws.py` (a real `websockets` client)
   connected to `ws://localhost:8001/api/v1/ws/notifications?token=<access_token>`,
   confirmed the first message was exactly `{"type":"session.init","session_id":"..."}`,
   and confirmed the handshake response headers included all six security
   headers. `scripts/verify_ws_bad_token.py` confirmed an invalid token is
   rejected at the handshake (HTTP `403`, since the server closes before
   `accept()` — see "Auth design decisions" above) rather than connecting
   and then silently dropping.
10. **Generic 500 on an unhandled exception** — a temporary route
    (`@app.get("/__temp_verify_500")`, raising `RuntimeError` unconditionally)
    was added, the server restarted, and `curl`ed: `500
    {"detail":"Internal server error","request_id":"..."}` — no traceback,
    no exception message. **This is also what surfaced and got fixed the
    "500 response missing security headers" bug** described above under
    "Security headers". The temporary route was then removed and the
    server restarted again to confirm `GET /__temp_verify_500` is gone
    (`404`) and `GET /api/v1/health` is unaffected. Separately, probing
    `PATCH /api/v1/leads/not-a-number` (a non-numeric id against `Lead`'s
    integer pk) surfaced a second, smaller leak — Django's own internal
    field-conversion message (`"Field 'id' expected a number but got
    'not-a-number'."`) was being returned verbatim in a `400` response via
    an over-broad `except ValueError` in `leads.py`. Fixed by normalizing
    any pk-conversion failure to a plain `Lead.DoesNotExist` → generic `404
    {"detail":"Lead not found"}`, re-verified after the fix.
11. **Clean shutdown** — the dev server process was stopped
    (`Stop-Process`), and a follow-up `curl` confirmed connection refused.

All eleven steps passed on the final code (not a pre-fix snapshot) — the two
genuine bugs step 10 surfaced (missing headers on 500s; a minor internal
message leak on a malformed lead id) were fixed and re-verified before this
report, not left as known issues.

## Notes for the root integrator (Docker Compose / nginx / CI)

- **This image doesn't contain `backend/`.** The Dockerfile only bakes in
  `api/`'s own source. The sibling Django project (whose ORM this service
  calls in-process) must be mounted or copied into the container at the
  path `BACKEND_DIR` points to — typically a bind mount of `../backend` to
  e.g. `/backend` in compose, with `BACKEND_DIR=/backend` set in the
  container's env. This also means **both containers need the same Python
  dependency versions for `Django`/`django-environ`/`PyJWT`** (already
  pinned identically here) **plus this service's extra transitive pins**
  (`celery`, `django-cors-headers`, `djangorestframework`, `Pillow` — see
  "Dependency management" above) if they're meant to run from genuinely
  separate installs rather than a shared volume/image layer.
- **Port mismatch to double-check:** this service's own Dockerfile
  `EXPOSE`s **8001** (per spec) and `app/core/uvicorn_worker.py` defaults to
  port 8001, matching `frontend-app/vite.config.ts`'s dev proxy
  (`target: 'http://localhost:8001'`). However
  `frontend-app/nginx.conf`'s production reverse-proxy is currently written
  as `proxy_pass http://api:8000/api/;` — **port 8000, not 8001** — with a
  comment in that file already flagging it as a placeholder for the root
  compose/nginx pass to fix. Whoever wires up production nginx needs to
  either change that to port `8001` or change this service to listen on
  `8000` in that environment — they currently disagree.
- **Redis**: both this service and `backend/` need `REDIS_URL` pointed at
  the *same* instance in production for the bridge-jti replay check and
  refresh-token revocation to mean anything cross-service; locally, neither
  needs Redis running at all (see "Auth design decisions" above).
- **`SHARED_JWT_SECRET`** must be identical in both services' production
  secrets, generated with real entropy
  (`python -c "import secrets; print(secrets.token_urlsafe(64))"`), never
  the local-dev placeholder.
- No `tests/` suite is included yet (see "Running tests" above) — CI should
  budget for adding one before gating merges on it.

## Notes for the React engineer (informational — nothing to act on)

Everything in `frontend-app/src/lib/{apiClient,authApi,types,tokenStore,safeJson}.ts`
and `hooks/useNotifications.ts` was read before writing this service and
matches the contract implemented here exactly, including:

- `credentials: "include"` + `Authorization: Bearer` + one-shot 401→refresh→retry
  (`apiClient.ts`) — this service's cookie `Path=/api/v1/auth` and CORS
  `allow_credentials=True` support this as written.
- The `AuthTokenResponse`/`CurrentUser`/`Lead`/`Post`/`HealthResponse`/
  `NotificationMessage` shapes in `types.ts` match `app/api/v1/schemas.py`
  field-for-field, including `id: string` on `Lead`/`Post` (see above).
- `useNotifications.ts`'s reconnect-with-backoff logic needs nothing special
  from the server beyond a clean close, which this implementation provides.

One cosmetic mismatch worth knowing about, not a bug: `types.ts` declares
`PostStatus` as `'draft' | 'published' | 'archived'`, but
`backend/apps/blog/models.py::Post.Status` only has `draft`/`published` — this
service only ever emits one of those two real values for `status`, `archived`
is simply a value the frontend type permits that the backend will never
produce today.
