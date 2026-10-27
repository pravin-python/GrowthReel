// Thin wrapper around fetch for all `/api/v1/...` calls that need
// authentication (leads, posts, me, ...). Rules enforced here:
//   1. Always sends credentials: "include" (needed so the browser attaches
//      the httpOnly refresh_token cookie set by /auth/exchange).
//   2. Always attaches `Authorization: Bearer <access_token>` when we have one.
//   3. On a 401, attempts exactly one silent refresh and retries the request
//      once with the new token before giving up.
//
// Auth endpoints themselves (/auth/exchange, /auth/refresh, /auth/logout)
// are NOT called through here — see src/lib/authApi.ts — to avoid the 401
// retry logic trying to "refresh" a refresh call.

import { safeJson } from './safeJson'
import { getAccessToken, setAccessToken } from './tokenStore'

export const API_BASE = '/api/v1'

export interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
}

export type ApiResult<T> =
  | { ok: true; data: T; status: number }
  | { ok: false; error: string; status: number }

function buildHeaders(options: ApiRequestOptions): Headers {
  const headers = new Headers(options.headers)
  const token = getAccessToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  if (options.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  return headers
}

async function rawFetch(path: string, options: ApiRequestOptions): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    ...options,
    headers: buildHeaders(options),
    credentials: 'include',
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  })
}

// Deduplicated so concurrent 401s (e.g. several widgets fetching on mount)
// trigger a single /auth/refresh call instead of a stampede.
let inFlightRefresh: Promise<boolean> | null = null

export async function silentRefresh(): Promise<boolean> {
  if (!inFlightRefresh) {
    inFlightRefresh = (async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
        })
        if (!response.ok) {
          setAccessToken(null)
          return false
        }
        const result = await safeJson<{ access_token: string }>(response)
        if (!result.ok) {
          setAccessToken(null)
          return false
        }
        setAccessToken(result.data.access_token)
        return true
      } catch {
        setAccessToken(null)
        return false
      } finally {
        inFlightRefresh = null
      }
    })()
  }
  return inFlightRefresh
}

export async function apiFetch(path: string, options: ApiRequestOptions = {}): Promise<Response> {
  let response = await rawFetch(path, options)

  if (response.status === 401) {
    const refreshed = await silentRefresh()
    if (refreshed) {
      response = await rawFetch(path, options)
    }
  }

  return response
}

/** Fetch + parse JSON in one call, using safeJson so a malformed body never throws. */
export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<ApiResult<T>> {
  const response = await apiFetch(path, options)

  if (response.status === 204) {
    return { ok: true, data: undefined as T, status: response.status }
  }

  const parsed = await safeJson<T>(response)

  if (!response.ok) {
    const error = parsed.ok ? summarizeErrorBody(parsed.data) : parsed.error
    return { ok: false, error, status: response.status }
  }

  if (!parsed.ok) {
    return { ok: false, error: parsed.error, status: response.status }
  }

  return { ok: true, data: parsed.data, status: response.status }
}

function summarizeErrorBody(data: unknown): string {
  if (data && typeof data === 'object' && 'detail' in data) {
    const detail = (data as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
  }
  return 'Request failed'
}
