import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { installMocks, uninstallMocks } from '../mocks'

describe('mock API layer', () => {
  beforeEach(() => {
    installMocks()
  })

  afterEach(() => {
    uninstallMocks()
  })

  it('answers GET /api/v1/health', async () => {
    const res = await fetch('/api/v1/health')
    expect(res.status).toBe(200)
    await expect(res.json()).resolves.toEqual({ status: 'ok' })
  })

  it('rejects an empty/invalid bridge token on exchange', async () => {
    const res = await fetch('/api/v1/auth/exchange', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bridge_token: 'expired' }),
    })
    expect(res.status).toBe(401)
  })

  it('exchanges a valid bridge token for an access token and sets the refresh cookie', async () => {
    const res = await fetch('/api/v1/auth/exchange', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bridge_token: 'good-token' }),
    })
    expect(res.status).toBe(200)
    const body = await res.json()
    expect(body).toMatchObject({ token_type: 'bearer', expires_in: 900 })
    expect(typeof body.access_token).toBe('string')
    expect(document.cookie).toContain('gr_mock_refresh=valid')
  })

  it('rejects reuse of an already-used bridge token (single-use enforcement)', async () => {
    const payload = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bridge_token: 'one-shot' }),
    }
    const first = await fetch('/api/v1/auth/exchange', payload)
    expect(first.status).toBe(200)

    const second = await fetch('/api/v1/auth/exchange', payload)
    expect(second.status).toBe(401)
  })

  it('silently refreshes when the mock refresh cookie is present', async () => {
    await fetch('/api/v1/auth/exchange', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bridge_token: 'refresh-setup' }),
    })

    const refreshRes = await fetch('/api/v1/auth/refresh', { method: 'POST' })
    expect(refreshRes.status).toBe(200)
    const body = await refreshRes.json()
    expect(typeof body.access_token).toBe('string')
  })

  it('401s on refresh with no session', async () => {
    const res = await fetch('/api/v1/auth/refresh', { method: 'POST' })
    expect(res.status).toBe(401)
  })

  it('requires a bearer token for /api/v1/leads and supports the status filter', async () => {
    const unauthed = await fetch('/api/v1/leads')
    expect(unauthed.status).toBe(401)

    const authed = await fetch('/api/v1/leads', {
      headers: { Authorization: 'Bearer test-token' },
    })
    expect(authed.status).toBe(200)
    const all = await authed.json()
    expect(Array.isArray(all)).toBe(true)
    expect(all.length).toBeGreaterThan(0)

    const filtered = await fetch('/api/v1/leads?status=won', {
      headers: { Authorization: 'Bearer test-token' },
    })
    const wonLeads = await filtered.json()
    expect(wonLeads.every((l: { status: string }) => l.status === 'won')).toBe(true)
  })

  it('updates a lead status via PATCH', async () => {
    const list = await fetch('/api/v1/leads', { headers: { Authorization: 'Bearer test-token' } }).then((r) =>
      r.json(),
    )
    const target = list[0]

    const patched = await fetch(`/api/v1/leads/${target.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer test-token' },
      body: JSON.stringify({ status: 'won' }),
    })
    expect(patched.status).toBe(200)
    const updated = await patched.json()
    expect(updated.status).toBe('won')
  })

  it('returns posts for an authenticated request', async () => {
    const res = await fetch('/api/v1/posts', { headers: { Authorization: 'Bearer test-token' } })
    expect(res.status).toBe(200)
    const posts = await res.json()
    expect(Array.isArray(posts)).toBe(true)
    expect(posts.length).toBeGreaterThan(0)
  })
})
