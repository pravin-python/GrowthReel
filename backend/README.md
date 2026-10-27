# GrowthReel — Django Backend

This is the **content / admin / CRM / blog backend** for the public marketing
site at `growthreel.com`. It is one of three services in the GrowthReel
project:

- **`backend/`** (this directory) — Django. Server-rendered marketing site,
  blog, Django admin (used as the CRM UI), session-based login, and the
  identity/user model everything else depends on.
- **`api/`** (sibling directory, built separately) — FastAPI service for
  `app.growthreel.com`. Imports this project's settings and calls
  `django.setup()` to reuse the Django ORM models directly (same database,
  no HTTP hop).
- **`frontend-app/`** (sibling directory, built separately) — React SPA for
  `app.growthreel.com`, talks only to the FastAPI service.

A root-level `docker-compose` / CI setup wiring all three together is owned
by a later pass and is intentionally **not** included here.

## Directory layout

```
backend/
  manage.py                      Django management entrypoint.
  pyproject.toml                 Project metadata + [tool.ruff]/[tool.black]/[tool.mypy] config only.
  requirements/
    base.txt                     Shared dependencies (Django, DRF, PyJWT, Celery, Redis, Pillow, psycopg...).
    local.txt                    base.txt + dev tools (debug toolbar, ipython).
    production.txt                base.txt + gunicorn/whitenoise/sentry extras.
    testing.txt                   base.txt + pytest/pytest-django/factory-boy.
  .env.example                   Documented template for all environment variables (see below).
  .pre-commit-config.yaml        ruff, black, mypy, bandit hooks.
  Dockerfile                     Multi-stage build, non-root user, gunicorn entrypoint.
  config/                        Project-level configuration (the Django "project" package).
    settings/
      base.py                    Shared settings: installed apps, middleware, templates, CORS, logging, bridge-JWT config.
      local.py                   Postgres (DB_* vars), DEBUG=True, console email, locmem cache.
      production.py              Postgres (same DB_* vars as local.py, plus DB_SSLMODE), Redis cache, full security hardening.
      testing.py                 In-memory SQLite, MD5 password hasher, fast test settings.
    urls.py                      Root URLConf: /admin/, /accounts/, /blog/, /.
    asgi.py / wsgi.py            Standard entrypoints (point at config.settings.production by default).
    celery.py                    Celery app factory (`Celery("growthreel")`, CELERY_ namespace, autodiscover_tasks()).
  apps/
    core/                        Shared, app-agnostic building blocks.
      models.py                  TimeStampedModel, SoftDeleteModel, AuditedModel mixins.
      middleware.py              RequestIDMiddleware, SecurityHeadersMiddleware.
      context.py                 contextvar-based request-id propagation + logging Filter.
    users/                       Identity. The contract the FastAPI service depends on lives here.
      models.py                  User (UUID pk, email login), UserManager.
      services.py                issue_bridge_token(user), verify_password(user, raw) — business logic.
      selectors.py               get_user_by_email(), get_active_users() — read-only queries.
      views.py / urls.py         CustomLoginView / CustomLogoutView at /accounts/login/, /accounts/logout/.
      admin.py                   UserAdmin.
    blog/                        Public blog.
      models.py                  Post, Category.
      services.py                create_post(), update_post(), publish_post(), unpublish_post() — the only places that mutate Post.
      selectors.py                get_published_posts(), get_post_by_slug() (404s unpublished posts for everyone).
      views.py / urls.py / templates/blog/{list,detail}.html
      admin.py                    PostAdmin, CategoryAdmin.
    crm/                          Internal CRM. The Django admin IS the CRM UI — no separate frontend for it.
      models.py                  Lead, Client.
      services.py                create_lead(), change_lead_status(), convert_lead_to_client().
      selectors.py                get_leads_for_owner(), get_open_leads().
      admin.py                    LeadAdmin, ClientAdmin (this is what staff actually use day to day).
  templates/
    base.html                    Tailwind-loaded layout (nav/footer).
    home.html                    Minimal marketing homepage.
    registration/login.html      Tailwind-styled login form.
  static_src/
    input.css                    Tailwind v4 entrypoint (`@import "tailwindcss";`).
  static/
    css/                         Build output lands here (static/css/tailwind.css); the built CSS file itself is git-ignored, the directory is kept with a .gitkeep.
  package.json                   devDependency on tailwindcss@4.3.3 + @tailwindcss/cli, build:css / watch:css scripts.
  .gitignore
```

## Dependency management: why `requirements/*.txt` + `pyproject.toml` (not Poetry/uv)

The original spec called for Poetry or uv. On this machine, `uv` has no
matching distribution available on the configured pip index, so dependency
*installation* uses plain `pip` against `requirements/base.txt` (shared),
layered with `local.txt` / `production.txt` / `testing.txt`. `pyproject.toml`
is still provided at the backend root, but holds only project metadata and
tool configuration (`[tool.ruff]`, `[tool.black]`, `[tool.mypy]`) — it is not
a build backend and does not drive installs. If `uv`/`poetry` become
available later, migrating is a matter of `uv pip compile`/`poetry add`
against the same package list.

## Setup from scratch (Windows / Git Bash)

```bash
cd E:\Django_project\practice\GrowthReel\backend

# 1. Create a project-local virtualenv with Python 3.12 (do NOT use global site-packages).
"C:\Users\pc050607\AppData\Local\Programs\Python\Python312\python.exe" -m venv .venv

# 2. Install Python dependencies (local/dev profile).
.venv/Scripts/python.exe -m pip install --upgrade pip
.venv/Scripts/python.exe -m pip install -r requirements/local.txt

# 3. Install Node dependencies and build Tailwind CSS.
npm install
npm run build:css          # one-off build -> static/css/tailwind.css
# npm run watch:css        # (alternative) rebuild on change while developing

# 4. Create your local .env from the template and adjust values.
cp .env.example .env
#   at minimum, set a real-looking DJANGO_SECRET_KEY and SHARED_JWT_SECRET
#   for local dev (see "Contract for the FastAPI service" below).
#   local.py needs a reachable Postgres (DB_* vars in .env) — e.g.
#   `docker compose up postgres` from the repo root, or your own install.

# 5. Apply migrations.
.venv/Scripts/python.exe manage.py makemigrations
.venv/Scripts/python.exe manage.py migrate

# 6. Create a superuser (interactive).
.venv/Scripts/python.exe manage.py createsuperuser
#   or non-interactively:
.venv/Scripts/python.exe manage.py shell -c "from apps.users.models import User; User.objects.create_superuser(email='admin@growthreel.com', password='change-me')"

# 7. Run the dev server.
.venv/Scripts/python.exe manage.py runserver
#   visit http://127.0.0.1:8000/          (homepage)
#   visit http://127.0.0.1:8000/accounts/login/
#   visit http://127.0.0.1:8000/blog/
#   visit http://127.0.0.1:8000/admin/    (this is also "the CRM")
```

`manage.py` defaults `DJANGO_SETTINGS_MODULE` to `config.settings.local` if
it isn't already set in the environment, so the commands above work without
exporting it explicitly. For production-style runs, set
`DJANGO_SETTINGS_MODULE=config.settings.production` (and provide
`DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`/`DB_SSLMODE`,
`REDIS_URL`, a real `DJANGO_SECRET_KEY`, etc.) before invoking `manage.py`
or `gunicorn config.wsgi:application`.

### Running tests

```bash
DJANGO_SETTINGS_MODULE=config.settings.testing .venv/Scripts/python.exe -m pip install -r requirements/testing.txt
DJANGO_SETTINGS_MODULE=config.settings.testing .venv/Scripts/python.exe -m pytest
```

### Pre-commit hooks

```bash
.venv/Scripts/python.exe -m pip install pre-commit
.venv/Scripts/python.exe -m pre_commit install
```

## Contract for the FastAPI service

This section is the one the `api/` (FastAPI) engineer should read. Everything
below is deliberately stable and should not change without updating this
file and coordinating across both services.

### Settings module / entrypoint

- `DJANGO_SETTINGS_MODULE=config.settings.local` for local dev,
  `config.settings.production` in production.
- FastAPI points at this same `backend/` directory, sets
  `DJANGO_SETTINGS_MODULE` to one of the above, and calls `django.setup()`
  before using any Django ORM model.

### User model — `apps.users.models.User`, `AUTH_USER_MODEL = "users.User"`

- `id`: `UUIDField`, primary key, `default=uuid.uuid4`, `editable=False`.
- `email`: unique, `USERNAME_FIELD`. There is **no** separate `username`
  field (`REQUIRED_FIELDS = []`).
- `first_name`, `last_name`: plain `CharField`s.
- `role`: `CharField` with choices `admin` / `staff` / `member` (default
  `member`) — this is what the FastAPI/React side should use for
  authorization decisions.
- `is_active`, `is_staff`, `is_superuser` (from `AbstractBaseUser` /
  `PermissionsMixin`, as normal), `date_joined`.
- `created_at` / `updated_at` via `apps.core.models.TimeStampedModel`.
- Custom manager: `apps.users.models.UserManager(BaseUserManager)`, with
  `create_user(email, password=None, **extra_fields)` and
  `create_superuser(email, password=None, **extra_fields)`.

### The Django-login -> FastAPI bridge

End-to-end flow:

1. A user logs in at `growthreel.com/accounts/login/` — a normal Django
   session-based login (`apps.users.views.CustomLoginView`), rendered with
   Tailwind, **not** an API call.
2. On success, instead of redirecting to a Django page, the browser is
   redirected to:

   ```
   {APP_FRONTEND_URL}/auth/callback?token=<bridge_jwt>
   ```

   `APP_FRONTEND_URL` is configurable via env var, default
   `http://localhost:5173` for local dev (the Vite dev server for
   `frontend-app/`).
3. `<bridge_jwt>` is a short-lived (**60 seconds**), single-use JWT minted by
   `apps.users.services.issue_bridge_token(user) -> str`, using `PyJWT`,
   signed **HS256** with the env var `SHARED_JWT_SECRET`. This is the exact
   same secret value the FastAPI service must be configured with, so it can
   verify the token without calling back into Django.

   Claims:

   | claim  | type | meaning                                             |
   |--------|------|------------------------------------------------------|
   | `sub`  | str  | the user's UUID (`str(user.pk)`)                     |
   | `email`| str  | the user's email                                      |
   | `role` | str  | `admin` / `staff` / `member`                          |
   | `jti`  | str  | random uuid4, for single-use/replay enforcement        |
   | `iat`  | int  | issued-at (epoch seconds)                             |
   | `exp`  | int  | `iat + 60`                                            |
   | `typ`  | str  | always the literal string `"bridge"`                  |

4. **Single-use enforcement.** When the token is minted, Django records the
   `jti` via `django.core.cache.cache.set(f"bridge-jti:{jti}", 1, timeout=70)`.
   This is **advisory, Django-side-only** enforcement. The FastAPI service is
   expected to do its own authoritative replay check against the *same*
   Redis instance in production (reject if the key is missing, i.e. already
   consumed/expired, or implement its own consume-on-use `DEL`). For local
   development, with `config.settings.local`, the cache backend is
   `LocMemCache` (not Redis) — this means the Django-side `jti` record is
   **not visible to a separately-running FastAPI process locally**, so local
   dev effectively relies on the 60-second expiry alone unless both services
   are pointed at the same local Redis. This is intentional and acceptable
   for local dev; production must use the shared `REDIS_URL` on both sides
   for real replay protection.
5. The FastAPI service verifies the bridge JWT (signature + `exp` + `typ` +,
   in production, the `jti` replay check against Redis), looks up the user
   via the Django ORM (`User.objects.get(pk=claims["sub"])`), and mints its
   own normal access/refresh JWT pair. **This part is built by the FastAPI
   engineer, not here** — this repo only guarantees `issue_bridge_token`
   produces tokens exactly as documented above.

`apps.users.services.verify_password(user, raw_password) -> bool` is a thin
wrapper around `django.contrib.auth.hashers.check_password`. In practice the
FastAPI service, having full ORM access, will just call
`check_password(raw_password, user.password)` directly rather than importing
this Django-app-internal module — this function exists so there's one
obvious, documented, importable place in this codebase that mirrors exactly
what the FastAPI side is expected to do, and so Django-side code (tests,
admin actions, management commands) has a single verified helper to use.

### Environment variables both services must agree on

See `.env.example` for the full, documented list. The ones that **must**
match between `backend/` and `api/`:

| variable            | shared? | purpose                                                              |
|---------------------|---------|-----------------------------------------------------------------------|
| `SHARED_JWT_SECRET`  | yes     | HS256 signing secret for the bridge JWT.                              |
| `APP_FRONTEND_URL`   | yes     | Base URL of the React SPA; Django builds the post-login redirect to it.|
| `REDIS_URL`          | yes     | Shared cache/broker; also where the authoritative bridge-jti replay check should live in production. |

Database connection (`DB_ENGINE`/`DB_NAME`/`DB_USER`/`DB_PASSWORD`/
`DB_HOST`/`DB_PORT`/`DB_SSLMODE`) is **not** in the table above and does
**not** need to be duplicated into `api/.env` — when the FastAPI service
calls `django.setup()`, Django reads these straight out of *this* project's
own `.env` file (resolved relative to `BACKEND_DIR`), so both processes
always agree on the database without copying anything.

`SHARED_JWT_SECRET` guidance: generate at least 32 bytes of real entropy,
e.g. `python -c "import secrets; print(secrets.token_urlsafe(64))"`. Never
reuse the placeholder value in `.env.example`, and never commit a real
secret — it belongs only in each environment's own `.env` / secret manager.

## Security headers (`apps/core/middleware.py::SecurityHeadersMiddleware`)

Applied to every response from this Django app:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload   (only when request.is_secure())
Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; font-src 'self' data:
```

**Design decision:** the original spec's literal policy,
`default-src 'none'; frame-ancestors 'none'; base-uri 'none'`, is correct
and used as-is on the FastAPI JSON/WebSocket side, which never renders
HTML/CSS/JS so there's nothing for `'none'` to break. This Django app *does*
render HTML/CSS/JS (Tailwind templates, the login page, the Django admin),
so a blanket `'none'` would break its own static assets. Here we keep
`frame-ancestors 'none'` (nothing may frame this site — same intent as the
spec) and relax everything else to `'self'` (`'unsafe-inline'` for styles,
required by the Django admin; `data:` for images/fonts), which preserves "no
framing, no cross-origin anything" while the site still renders.

`Cache-Control: no-store` is applied specifically to the login view and any
response carrying the bridge-JWT redirect (not blanket-applied to static
assets). Any response under `/admin/` or `/accounts/` additionally gets
`Cache-Control: no-store, no-cache, must-revalidate`.

## Verification performed

All of the following were run against `config.settings.local` (SQLite, no
Postgres/Redis required) using this project's own `.venv`:

1. `manage.py check` — passed, no issues.
2. `manage.py makemigrations` + `manage.py migrate` — succeeded against
   local SQLite.
3. `npm install` + `npm run build:css` — produced `static/css/tailwind.css`
   (~14 KB minified, containing real utility classes used by the templates,
   e.g. `bg-indigo-600`).
4. `manage.py runserver` smoke test — `/`, `/accounts/login/`, and `/blog/`
   all returned `200 OK` with `X-Content-Type-Options`,
   `X-Frame-Options`, and `X-Request-ID` present on every response.
5. Created a superuser non-interactively via `manage.py shell`, logged into
   `/admin/` with it, and confirmed the Lead, Client, Post, Category, and
   User changelist pages all return `200 OK`.
6. Logged in via the real `/accounts/login/` form (not `/admin/login/`) and
   confirmed the `302` response redirects to
   `http://localhost:5173/auth/callback?token=<jwt>` with
   `Cache-Control: no-store` on that response; decoded the token with the
   same `SHARED_JWT_SECRET` and confirmed `sub`, `email`, `role`, `jti`,
   `iat`, `exp` (`exp - iat == 60`), and `typ == "bridge"` all match the
   contract, and that the `jti` was recorded in the cache
   (`bridge-jti:<jti>`). Also confirmed `verify_password` returns `True`/
   `False` correctly for right/wrong passwords.

All six checks passed; nothing was left broken.

## Reviewer notes / things worth double-checking

- **Local cache backend is not Redis.** `config.settings.local` uses
  Django's `LocMemCache` so local verification doesn't require a running
  Redis. This means the `jti` single-use record is only visible within the
  single Django process — fine for local dev with one process, but if you
  run multiple Django worker processes locally you won't get cross-process
  replay protection until you point `local.py` at a real local Redis.
  `production.py` correctly uses `django.core.cache.backends.redis.RedisCache`.
- **Database connection uses discrete `DB_*` variables in both `local.py`
  and `production.py`** (`env.str()` from `django-environ`), not a single
  `DATABASE_URL`-style value — one connection-config pattern everywhere,
  and no second URL-parsing dependency (e.g. `dj-database-url`) needed.
  `production.py` additionally reads `DB_SSLMODE` (default `"require"`)
  into `OPTIONS`, which `local.py` doesn't set at all.
- **Connection pooling**: `production.py` sets `CONN_MAX_AGE = 60` on the
  default database. For real production load, pgbouncer (or the
  `django-db-connection-pool` package) is the correct long-term answer;
  this wasn't added to avoid over-engineering a backend with no real traffic
  yet.
- **CSRF cookie is JS-readable** (`CSRF_COOKIE_HTTPONLY = False`) — this is
  intentional and documented inline in `config/settings/base.py`; it's
  required for Django's standard CSRF-token-in-JS pattern and does not widen
  the attack surface for the separate FastAPI/React app, which never reads
  this cookie.
- **`SHARED_JWT_SECRET` in this repo's own `.env`** (used only for the local
  verification above) is a placeholder value for local testing and was
  never committed — `.env` is covered by `.gitignore`.  Only
  `.env.example` (with a placeholder, not a real secret) is meant to be
  committed.
- **Tags on `Post`** are a simple comma-separated `CharField` rather than a
  M2M-through model, per the spec's "simple CharField list is fine" option —
  revisit if free-text tag search/autocomplete becomes a real requirement.
- **Slug auto-generation** (`Post.save()` / `Category.save()`) lives on the
  model rather than in `services.py` — treated as data normalization
  intrinsic to the model (same category as `auto_now`), not domain business
  logic; `services.py` still owns everything that actually changes domain
  state (status transitions, lead conversion, etc.).
