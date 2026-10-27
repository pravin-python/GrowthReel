# GrowthReel — frontend-app

The authenticated SPA served at `app.growthreel.com`. It is the dashboard users
land on after logging into the separate Django marketing site (`growthreel.com`).
This app talks **only** to the FastAPI backend (`/api/v1/...` + one WebSocket) —
never directly to Django.

Stack: Vite + React + TypeScript, Tailwind CSS v4 (`4.3.3` via `@tailwindcss/vite`),
React Router, plain React context for auth state (no Redux/Zustand).

## Setup

```bash
npm install
cp .env.example .env   # adjust VITE_MARKETING_SITE_URL / VITE_USE_MOCKS as needed
npm run dev            # http://localhost:5173
```

In dev, requests to `/api/...` are proxied (see `vite.config.ts`) to
`http://localhost:8001`, where the sibling FastAPI service is expected to run.
In production, the same relative `/api/v1/...` paths are used — the deploy
environment (nginx/reverse proxy, see `nginx.conf` / `Dockerfile`) is expected
to forward `/api` to the FastAPI service. This lets the app call identical
paths in both environments.

### Scripts

| Command           | Purpose                                      |
| ------------------ | --------------------------------------------- |
| `npm run dev`      | Start the Vite dev server                     |
| `npm run build`    | Type-check (`tsc -b`) + production build      |
| `npm run preview`  | Preview the production build locally          |
| `npm test`         | Run the Vitest unit test suite                |
| `npm run lint`     | Run oxlint                                    |

## The SSO handoff flow

1. A user logs into `growthreel.com` (Django — not part of this repo).
2. Django redirects the browser to
   `https://app.growthreel.com/auth/callback?token=<bridge_jwt>`, where
   `<bridge_jwt>` is a short-lived, single-use JWT.
3. `/auth/callback` (`src/pages/AuthCallbackPage.tsx`) reads `token` from the
   query string and `POST`s it to `/api/v1/auth/exchange` with
   `{"bridge_token": "<token>"}`. On success the backend returns
   `{"access_token", "token_type", "expires_in"}` and sets an httpOnly
   `refresh_token` cookie itself — this app never reads or writes that cookie
   directly; it just always calls with `credentials: "include"` so the browser
   attaches/accepts it automatically. The access token is stored **in memory
   only** (`src/lib/tokenStore.ts`, exposed via `AuthContext`) and the app
   redirects to `/dashboard`.
4. If the exchange fails (expired/invalid/already-used bridge token), the app
   redirects to `/login-expired`, which explains the link expired and links
   back to `${VITE_MARKETING_SITE_URL}/accounts/login/`.
5. On every app load with no in-memory token (e.g. a hard reload landing
   directly on `/dashboard`), `ProtectedRoute` (`src/components/ProtectedRoute.tsx`)
   attempts a silent refresh: `POST /api/v1/auth/refresh` with
   `credentials: "include"`, relying entirely on the httpOnly cookie. A
   `{"access_token": ...}` response means the user is logged back in; a 401
   sends them to `/login-expired`.
6. `src/lib/apiClient.ts` attaches `Authorization: Bearer <access_token>` to
   every request, always sends `credentials: "include"`, and on a 401 performs
   exactly one silent-refresh-and-retry before giving up.
7. Logging out (`src/context/AuthContext.tsx` → `src/lib/authApi.ts`) calls
   `POST /api/v1/auth/logout` (`credentials: "include"`), clears the in-memory
   token, and sends the browser to the marketing site's login page.

### Why the access token is never persisted

`localStorage`/`sessionStorage` are readable by any script running on the
page, so a single XSS bug would let an attacker read out a persisted bearer
token and reuse it until it expires (or forever, if it were a refresh token).
Keeping the access token in a plain in-memory JS variable
(`src/lib/tokenStore.ts`) means it disappears on tab close/reload; the httpOnly
refresh cookie (which JS can never read, XSS or not) is what makes the user's
session durable across reloads via the silent-refresh flow above.

## API contract (`/api/v1`, same-origin via dev proxy)

| Method & path                      | Auth      | Body                      | Response                                                                 |
| ----------------------------------- | --------- | ------------------------- | ------------------------------------------------------------------------ |
| `POST /auth/exchange`               | none      | `{bridge_token}`          | `{access_token, token_type, expires_in}` + sets `refresh_token` cookie. 401 if invalid/expired/reused. |
| `POST /auth/refresh`                | cookie    | —                         | `{access_token, token_type, expires_in}`. 401 if no/expired cookie.      |
| `POST /auth/logout`                 | cookie    | —                         | 204, clears refresh cookie.                                              |
| `GET /auth/me`                      | Bearer    | —                         | `{id, email, first_name, last_name, role}`                               |
| `GET /health`                       | none      | —                         | `{status: "ok"}`                                                         |
| `GET /leads?status=`                | Bearer    | —                         | `[{id, name, email, phone, company, status, source, owner_id, created_at}]` |
| `PATCH /leads/{id}`                 | Bearer    | `{status}`                | Updated lead object.                                                     |
| `GET /posts`                        | Bearer    | —                         | `[{id, title, slug, status, published_at, author_email}]`                |
| `WS /ws/notifications?token=<jwt>`  | query tok | —                         | First: `{"type":"session.init","session_id":"..."}`; then: `{"type":"notification","message":"..."}` |

Types for all of the above live in `src/lib/types.ts` — treat it as the
single source of truth for the exact shapes this frontend assumes.

## Mock mode (`VITE_USE_MOCKS`)

Because the FastAPI service may not exist yet while this app is being built,
`src/mocks/` implements the full contract above as an in-memory, hand-rolled
interceptor: when `VITE_USE_MOCKS=true`, `src/main.tsx` monkeypatches
`window.fetch` and `window.WebSocket` (see `src/mocks/index.ts`) before the
app renders, so every `/api/v1/...` call and the notifications WebSocket are
answered locally — including single-use bridge-token enforcement, a
cookie-simulated refresh session, and a `PATCH /leads/{id}` that actually
mutates the in-memory lead list.

A hand-rolled interceptor was chosen over MSW to avoid service-worker
registration/hot-reload flakiness in this environment; it is trivial to
install/uninstall from a unit test (see `src/test/mocks.test.ts`).

This is **off by default** (`VITE_USE_MOCKS=false` or unset) so real/production
builds always call the real FastAPI service. Toggle it in `.env`:

```bash
VITE_USE_MOCKS=true
```

## Verification performed

- `npm install` — succeeds.
- `npm run build` — succeeds, no TypeScript errors.
- `npm run dev` + `curl http://localhost:5173/` — confirmed `HTTP 200` and an
  HTML response.
- `npm test` (Vitest) — 13 tests covering: the mock layer's
  `/auth/exchange` (incl. single-use enforcement), `/auth/refresh`,
  `/auth/logout`, `/auth/me`, `/leads` (incl. `?status=` filter), `PATCH
  /leads/{id}`, `/posts`; and `apiClient`'s Authorization/credentials
  attachment, 401-then-refresh-then-retry behavior, refresh-also-fails
  behavior, and `safeJson`-backed handling of a non-JSON (e.g. HTML error
  page) response.
- Browser automation (available in this environment) was used to click
  through the real app with `VITE_USE_MOCKS=true`: `/auth/callback?token=test`
  → bridge-token exchange → `/dashboard` (user info + live WS notification
  feed) → `/dashboard/leads` (status filter + inline PATCH status change with
  optimistic UI update, confirmed in the rendered table) → `/dashboard/posts`
  → logout (redirects to the marketing login URL and clears the session, so a
  subsequent direct hit on `/dashboard` correctly bounces to
  `/login-expired`) → `/auth/callback?token=expired` (correctly bounces to
  `/login-expired` immediately).

## Project layout

```
src/
  components/      ProtectedRoute, DashboardLayout, StatusBadge, LoadingScreen
  context/         AuthContext (in-memory access token + current user)
  hooks/           useNotifications (WebSocket, reconnect w/ backoff)
  lib/             apiClient, authApi, safeJson, tokenStore, types
  mocks/           hand-rolled fetch/WebSocket mock of the FastAPI contract
  pages/           AuthCallbackPage, LoginExpiredPage, DashboardHomePage,
                   LeadsPage, PostsPage
  test/            Vitest unit tests + setup
```

## For the FastAPI implementer — please double-check

- `POST /auth/exchange` request body key is exactly `bridge_token` (snake_case).
- `POST /auth/refresh` takes no body and relies solely on the `refresh_token`
  httpOnly cookie; it must not require the bearer header.
- `GET /ws/notifications` expects the access token as a `token` **query
  string** parameter (`?token=<jwt>`), not a header (browsers can't set
  custom headers on a WebSocket handshake) — and must send
  `{"type":"session.init","session_id":"..."}` as the very first message.
- Lead `status` values this UI hardcodes as the only options:
  `new | contacted | qualified | won | lost`.
- Post `status` values this UI styles: `draft | published | archived`.
- Error bodies are read as `{"detail": "..."}` when present (see
  `summarizeErrorBody` in `src/lib/apiClient.ts`); anything else falls back to
  a generic "Request failed" message, so a different error shape won't crash
  the UI but will show a less specific message.
- `expires_in` is assumed to be seconds and is currently not used to
  proactively schedule a refresh — refresh only happens reactively on a 401.
  If you'd rather the frontend refresh proactively before expiry, flag it and
  this can be added to `AuthContext`.
