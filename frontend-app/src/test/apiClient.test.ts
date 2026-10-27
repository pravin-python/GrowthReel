import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiRequest } from '../lib/apiClient'
import { getAccessToken, setAccessToken } from '../lib/tokenStore'

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('apiClient', () => {
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    setAccessToken('initial-token')
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    setAccessToken(null)
    vi.restoreAllMocks()
  })

  it('attaches the Authorization header and credentials: include', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
    globalThis.fetch = fetchMock as unknown as typeof fetch

    await apiRequest('/health')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/health')
    expect(init.credentials).toBe('include')
    expect((init.headers as Headers).get('Authorization')).toBe('Bearer initial-token')
  })

  it('retries once via silent refresh after a 401, then succeeds with the new token', async () => {
    const fetchMock = vi.fn()
    // 1) original request -> 401
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'expired' }, 401))
    // 2) /auth/refresh -> new access token
    fetchMock.mockResolvedValueOnce(jsonResponse({ access_token: 'refreshed-token', token_type: 'bearer', expires_in: 900 }))
    // 3) retried original request -> success
    fetchMock.mockResolvedValueOnce(jsonResponse({ id: '1' }))
    globalThis.fetch = fetchMock as unknown as typeof fetch

    const result = await apiRequest<{ id: string }>('/leads/1')

    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/auth/refresh')
    expect(result).toEqual({ ok: true, data: { id: '1' }, status: 200 })
    expect(getAccessToken()).toBe('refreshed-token')
  })

  it('gives up and clears the token when refresh also fails', async () => {
    const fetchMock = vi.fn()
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'expired' }, 401))
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'no session' }, 401))
    globalThis.fetch = fetchMock as unknown as typeof fetch

    const result = await apiRequest('/leads/1')

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(result.ok).toBe(false)
    expect(getAccessToken()).toBeNull()
  })

  it('uses safeJson so a non-JSON (e.g. HTML error page) body does not throw', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('<html>502 Bad Gateway</html>', { status: 502, headers: { 'Content-Type': 'text/html' } }),
    )
    globalThis.fetch = fetchMock as unknown as typeof fetch

    const result = await apiRequest('/leads')

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.status).toBe(502)
    }
  })
})
