import { useEffect, useRef, useState } from 'react'
import { getAccessToken } from '../lib/tokenStore'
import type { NotificationMessage } from '../lib/types'

const MAX_MESSAGES = 50
const INITIAL_BACKOFF_MS = 1000
const MAX_BACKOFF_MS = 30000

interface UseNotificationsResult {
  sessionId: string | null
  messages: string[]
  connected: boolean
}

/**
 * Connects to GET /api/v1/ws/notifications?token=<access_token>, reconnecting
 * with exponential backoff on close, and exposes the latest notification
 * text plus the session id the server hands back on connect.
 */
export function useNotifications(): UseNotificationsResult {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<string[]>([])
  const [connected, setConnected] = useState(false)

  const socketRef = useRef<WebSocket | null>(null)
  const backoffRef = useRef(INITIAL_BACKOFF_MS)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const stoppedRef = useRef(false)

  useEffect(() => {
    stoppedRef.current = false

    const connect = () => {
      if (stoppedRef.current) return
      const token = getAccessToken()
      if (!token) {
        // No session yet — try again shortly rather than looping tightly.
        reconnectTimerRef.current = setTimeout(connect, INITIAL_BACKOFF_MS)
        return
      }

      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const url = `${protocol}://${window.location.host}/api/v1/ws/notifications?token=${encodeURIComponent(token)}`
      const socket = new WebSocket(url)
      socketRef.current = socket

      socket.onopen = () => {
        backoffRef.current = INITIAL_BACKOFF_MS
        setConnected(true)
      }

      socket.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as NotificationMessage
          if (data.type === 'session.init') {
            setSessionId(data.session_id)
          } else if (data.type === 'notification') {
            setMessages((prev) => [...prev.slice(-(MAX_MESSAGES - 1)), data.message])
          }
        } catch {
          if (import.meta.env.DEV) console.debug('[useNotifications] ignored malformed message')
        }
      }

      socket.onclose = () => {
        setConnected(false)
        if (stoppedRef.current) return
        reconnectTimerRef.current = setTimeout(connect, backoffRef.current)
        backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF_MS)
      }

      socket.onerror = () => {
        socket.close()
      }
    }

    connect()

    return () => {
      stoppedRef.current = true
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      socketRef.current?.close()
    }
  }, [])

  return { sessionId, messages, connected }
}
