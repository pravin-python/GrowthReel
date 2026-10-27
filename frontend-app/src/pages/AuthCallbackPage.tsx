import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { exchangeBridgeToken } from '../lib/authApi'
import { useAuth } from '../context/AuthContext'
import { LoadingScreen } from '../components/LoadingScreen'

/**
 * SSO handoff landing point: Django redirects the browser here with
 * `?token=<bridge_jwt>` after a successful login on growthreel.com. We
 * exchange that single-use token for an access token + httpOnly refresh
 * cookie, then drop the user onto /dashboard.
 */
export function AuthCallbackPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { completeLogin } = useAuth()
  const started = useRef(false)

  useEffect(() => {
    // Guards against React StrictMode's dev-only double-invoke, which would
    // otherwise spend this single-use bridge token twice.
    if (started.current) return
    started.current = true

    const bridgeToken = searchParams.get('token')
    if (!bridgeToken) {
      navigate('/login-expired', { replace: true })
      return
    }

    void (async () => {
      const result = await exchangeBridgeToken(bridgeToken)
      if (!result.ok) {
        navigate('/login-expired', { replace: true })
        return
      }
      await completeLogin()
      navigate('/dashboard', { replace: true })
    })()
  }, [searchParams, navigate, completeLogin])

  return <LoadingScreen message="Signing you in..." />
}
