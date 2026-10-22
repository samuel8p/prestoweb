import { refreshRequest } from './api'
import { clearSession, getRefreshToken, setSession } from './tokenStore'

/**
 * Renovación del access token.
 *
 * Vive fuera de React porque es un asunto del cliente HTTP y no del
 * componente: si dos peticiones reciben un `401` al mismo tiempo, ambas
 * comparten la misma renovación (el backend rota el refresh token, así que no
 * puede renovarse dos veces en paralelo).
 */
let inFlight: Promise<string | null> | null = null

/**
 * Renueva el access token usando el refresh token de la pestaña.
 *
 * @returns el access token nuevo, o `null` si no hay sesión o la renovación falla.
 */
export function refreshSession(): Promise<string | null> {
  if (inFlight) {
    return inFlight
  }

  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    return Promise.resolve(null)
  }

  const attempt = (async () => {
    try {
      const tokens = await refreshRequest(refreshToken)
      setSession(tokens.access, tokens.refresh)
      return tokens.access
    } catch {
      clearSession()
      return null
    } finally {
      inFlight = null
    }
  })()

  inFlight = attempt
  return attempt
}
