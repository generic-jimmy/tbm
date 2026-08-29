import { useEffect, useRef, useCallback } from 'react'
import { wsUrl } from '../api/client'

export function useWebSocket(onMessage, botHash = null) {
  const wsRef       = useRef(null)
  const retryRef    = useRef(null)
  const mountedRef  = useRef(true)

  const connect = useCallback(() => {
    if (!localStorage.getItem('tbm_token')) return
    const ws = new WebSocket(wsUrl(botHash))
    wsRef.current = ws

    ws.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)) } catch {}
    }
    ws.onclose = () => {
      if (mountedRef.current) {
        retryRef.current = setTimeout(connect, 3000)
      }
    }
    ws.onerror = () => ws.close()
  }, [botHash, onMessage])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      clearTimeout(retryRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return wsRef
}
