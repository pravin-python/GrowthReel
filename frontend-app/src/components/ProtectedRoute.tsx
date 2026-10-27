import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LoadingScreen } from './LoadingScreen'

/**
 * Gates dashboard routes. On first mount with no in-memory token (e.g. a
 * hard reload landing straight on /dashboard), attempts a silent,
 * cookie-based refresh; shows a loading state while that's in flight, then
 * renders its children or bounces to /login-expired.
 */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { status, accessToken, restoreSession } = useAuth()
  const attempted = useRef(false)

  useEffect(() => {
    if (attempted.current) return
    if (status === 'loading' && !accessToken) {
      attempted.current = true
      void restoreSession()
    }
  }, [status, accessToken, restoreSession])

  if (status === 'loading') {
    return <LoadingScreen message="Checking your session..." />
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/login-expired" replace />
  }

  return <>{children}</>
}
