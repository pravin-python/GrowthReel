// Hand-rolled dev-only mock layer for the FastAPI `/api/v1` contract.
//
// Chosen over MSW because it needs zero service-worker registration (which
// is finicky to get reliably hot-reloading under Vite + an npm-installed
// worker script) — a single `window.fetch` / `window.WebSocket` monkeypatch
// does the whole job and is trivial to install/uninstall from a unit test.
//
// Only ever active when VITE_USE_MOCKS=true (see main.tsx). Never imported
// into a code path that production builds reach with mocks off.

import type { CurrentUser, Lead, Post } from '../lib/types'
import { mockUser, seedLeads, seedPosts } from './data'

const REFRESH_COOKIE = 'gr_mock_refresh'

let leadsStore: Lead[] = seedLeads()
let postsStore: Post[] = seedPosts()
const usedBridgeTokens = new Set<string>()
let tokenCounter = 0

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function noContent(): Response {
  return new Response(null, { status: 204 })
}

function unauthorized(detail = 'Not authenticated'): Response {
  return json({ detail }, 401)
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

function setRefreshCookie() {
  document.cookie = `${REFRESH_COOKIE}=valid; path=/; max-age=3600; SameSite=Lax`
}

function clearRefreshCookie() {
  document.cookie = `${REFRESH_COOKIE}=; path=/; max-age=0; SameSite=Lax`
}

function issueAccessToken(): string {
  tokenCounter += 1
  return `mock-access-token-${tokenCounter}-${Date.now()}`
}

function bearerFrom(init?: RequestInit): string | null {
  const headers = new Headers(init?.headers)
  const auth = headers.get('Authorization')
  if (!auth?.startsWith('Bearer ')) return null
  const token = auth.slice('Bearer '.length).trim()
  return token.length > 0 ? token : null
}

function parseBody<T>(init?: RequestInit): T | null {
  if (typeof init?.body !== 'string') return null
  try {
    return JSON.parse(init.body) as T
  } catch {
    return null
  }
}

async function handleRequest(url: URL, init?: RequestInit): Promise<Response> {
  const method = (init?.method ?? 'GET').toUpperCase()
  const path = url.pathname

  if (path === '/api/v1/health' && method === 'GET') {
    return json({ status: 'ok' })
  }

  if (path === '/api/v1/auth/exchange' && method === 'POST') {
    const body = parseBody<{ bridge_token?: string }>(init)
    const bridgeToken = body?.bridge_token
    if (!bridgeToken || bridgeToken === 'expired' || usedBridgeTokens.has(bridgeToken)) {
      return unauthorized('Bridge token is invalid, expired, or already used')
    }
    usedBridgeTokens.add(bridgeToken)
    setRefreshCookie()
    return json({ access_token: issueAccessToken(), token_type: 'bearer', expires_in: 900 })
  }

  if (path === '/api/v1/auth/refresh' && method === 'POST') {
    if (getCookie(REFRESH_COOKIE) !== 'valid') {
      return unauthorized('No active session')
    }
    return json({ access_token: issueAccessToken(), token_type: 'bearer', expires_in: 900 })
  }

  if (path === '/api/v1/auth/logout' && method === 'POST') {
    clearRefreshCookie()
    return noContent()
  }

  if (path === '/api/v1/auth/me' && method === 'GET') {
    if (!bearerFrom(init)) return unauthorized()
    return json(mockUser satisfies CurrentUser)
  }

  if (path === '/api/v1/leads' && method === 'GET') {
    if (!bearerFrom(init)) return unauthorized()
    const status = url.searchParams.get('status')
    const data = status ? leadsStore.filter((l) => l.status === status) : leadsStore
    return json(data)
  }

  const leadMatch = path.match(/^\/api\/v1\/leads\/([^/]+)$/)
  if (leadMatch && method === 'PATCH') {
    if (!bearerFrom(init)) return unauthorized()
    const id = leadMatch[1]
    const body = parseBody<{ status?: Lead['status'] }>(init)
    const lead = leadsStore.find((l) => l.id === id)
    if (!lead) return json({ detail: 'Lead not found' }, 404)
    if (body?.status) lead.status = body.status
    leadsStore = leadsStore.map((l) => (l.id === id ? lead : l))
    return json(lead)
  }

  if (path === '/api/v1/posts' && method === 'GET') {
    if (!bearerFrom(init)) return unauthorized()
    return json(postsStore satisfies Post[])
  }

  return json({ detail: `Mock: no handler for ${method} ${path}` }, 404)
}

class MockNotificationSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  readyState = MockNotificationSocket.CONNECTING
  onopen: ((ev: Event) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  onclose: ((ev: CloseEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null

  private timers: ReturnType<typeof setTimeout>[] = []
  private sessionId = `mock-session-${Math.random().toString(36).slice(2, 10)}`
  url: string

  constructor(url: string) {
    this.url = url
    this.timers.push(
      setTimeout(() => {
        this.readyState = MockNotificationSocket.OPEN
        this.onopen?.(new Event('open'))
        this.emit({ type: 'session.init', session_id: this.sessionId })
        this.scheduleNotifications()
      }, 50),
    )
  }

  private scheduleNotifications() {
    let count = 0
    const tick = () => {
      if (this.readyState !== MockNotificationSocket.OPEN) return
      count += 1
      this.emit({ type: 'notification', message: `Mock notification #${count}` })
      this.timers.push(setTimeout(tick, 6000))
    }
    this.timers.push(setTimeout(tick, 6000))
  }

  private emit(data: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }))
  }

  send(): void {
    // The real server doesn't expect client->server messages in this contract.
  }

  close(): void {
    if (this.readyState === MockNotificationSocket.CLOSED) return
    this.readyState = MockNotificationSocket.CLOSED
    for (const t of this.timers) clearTimeout(t)
    this.onclose?.(new CloseEvent('close'))
  }
}

let originalFetch: typeof fetch | null = null
let originalWebSocket: typeof WebSocket | null = null
let installed = false

export function installMocks(): void {
  if (installed) return
  installed = true

  originalFetch = window.fetch.bind(window)
  window.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(typeof input === 'string' ? input : input.toString(), window.location.origin)
    if (url.pathname.startsWith('/api/v1')) {
      return handleRequest(url, init)
    }
    return originalFetch!(input, init)
  }) as typeof fetch

  originalWebSocket = window.WebSocket
  window.WebSocket = MockNotificationSocket as unknown as typeof WebSocket

  if (import.meta.env.DEV) {
    console.debug('[mocks] GrowthReel API mocks installed')
  }
}

/** Restores real fetch/WebSocket and resets in-memory data. Used by tests. */
export function uninstallMocks(): void {
  if (!installed) return
  if (originalFetch) window.fetch = originalFetch
  if (originalWebSocket) window.WebSocket = originalWebSocket
  installed = false
  leadsStore = seedLeads()
  postsStore = seedPosts()
  usedBridgeTokens.clear()
  clearRefreshCookie()
}
