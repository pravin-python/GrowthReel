// The in-memory access-token store.
//
// The access token lives ONLY here, as a module-level variable — never in
// localStorage or sessionStorage. Those are readable by any script on the
// page, so a successful XSS attack would be able to exfiltrate a persisted
// token and reuse it indefinitely. Keeping the token in JS memory means it
// disappears on tab close/reload (at which point `silentRefresh()` gets a
// fresh one from the httpOnly refresh cookie, which JS can never read).
//
// Exposed as a tiny pub/sub store so React (AuthContext) can subscribe to it
// with `useSyncExternalStore` and re-render when the token changes, while
// non-React code (apiClient) can read/write it directly without importing
// React at all.

type Listener = () => void

let accessToken: string | null = null
const listeners = new Set<Listener>()

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string | null): void {
  accessToken = token
  for (const listener of listeners) listener()
}

export function subscribeToken(listener: Listener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
