// The three auth endpoints that are NOT routed through apiClient's
// 401-retry wrapper (exchanging/refreshing/revoking a session should never
// itself trigger a "refresh and retry").

import { safeJson } from './safeJson'
import { apiRequest, silentRefresh } from './apiClient'
import { setAccessToken } from './tokenStore'
import type { AuthTokenResponse, CurrentUser } from './types'

const API_BASE = '/api/v1'

export type ExchangeResult =
  | { ok: true; data: AuthTokenResponse }
  | { ok: false; status: number }

export async function exchangeBridgeToken(bridgeToken: string): Promise<ExchangeResult> {
  try {
    const response = await fetch(`${API_BASE}/auth/exchange`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bridge_token: bridgeToken }),
    })

    if (!response.ok) {
      return { ok: false, status: response.status }
    }

    const result = await safeJson<AuthTokenResponse>(response)
    if (!result.ok) {
      return { ok: false, status: response.status }
    }

    setAccessToken(result.data.access_token)
    return { ok: true, data: result.data }
  } catch {
    return { ok: false, status: 0 }
  }
}

/** Attempt a silent, cookie-based refresh. Used on app load with no bridge token. */
export async function tryRestoreSession(): Promise<boolean> {
  return silentRefresh()
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    })
  } finally {
    setAccessToken(null)
  }
}

export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  const result = await apiRequest<CurrentUser>('/auth/me')
  return result.ok ? result.data : null
}
