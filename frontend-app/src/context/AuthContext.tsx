import { createContext, useCallback, useContext, useMemo, useState, useSyncExternalStore } from 'react'
import type { ReactNode } from 'react'
import { getAccessToken, subscribeToken } from '../lib/tokenStore'
import { fetchCurrentUser, logout as logoutRequest, tryRestoreSession } from '../lib/authApi'
import type { CurrentUser } from '../lib/types'

// NOTE on token storage: the access token is never read from or written to
// this context's state directly — it lives in src/lib/tokenStore.ts as a
// plain in-memory module variable, and this context merely subscribes to it
// via useSyncExternalStore. That keeps a single source of truth and means
// the token is NEVER persisted to localStorage/sessionStorage (both are
// readable by any injected script, so persisting a bearer token there would
// hand an XSS bug a long-lived credential). Losing the token on refresh is
// an intentional tradeoff: `silentRefresh()` transparently mints a new one
// from the httpOnly refresh cookie that the browser — not our JS — holds.

interface AuthContextValue {
  accessToken: string | null
  user: CurrentUser | null
  status: 'loading' | 'authenticated' | 'unauthenticated'
  restoreSession: () => Promise<boolean>
  completeLogin: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const accessToken = useSyncExternalStore(subscribeToken, getAccessToken)
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [status, setStatus] = useState<'loading' | 'authenticated' | 'unauthenticated'>('loading')

  const loadUser = useCallback(async () => {
    const me = await fetchCurrentUser()
    setUser(me)
    setStatus(me ? 'authenticated' : 'unauthenticated')
    return me !== null
  }, [])

  /** Called once on app load (e.g. landing on /dashboard with no bridge token). */
  const restoreSession = useCallback(async () => {
    setStatus('loading')
    const restored = await tryRestoreSession()
    if (!restored) {
      setStatus('unauthenticated')
      setUser(null)
      return false
    }
    return loadUser()
  }, [loadUser])

  /** Called right after /auth/callback successfully exchanges the bridge token. */
  const completeLogin = useCallback(async () => {
    setStatus('loading')
    await loadUser()
  }, [loadUser])

  const logout = useCallback(async () => {
    await logoutRequest()
    setUser(null)
    setStatus('unauthenticated')
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ accessToken, user, status, restoreSession, completeLogin, logout }),
    [accessToken, user, status, restoreSession, completeLogin, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
