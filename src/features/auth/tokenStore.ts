/**
 * Almacenamiento de los tokens de la sesión.
 *
 * - El **access token** vive solo en memoria: no se escribe en disco, así que
 *   no queda en el `localStorage` del navegador ni sobrevive a un cierre de
 *   pestaña.
 * - El **refresh token** va al `sessionStorage`: es el único lugar del
 *   navegador donde se puede guardar sin que sobreviva al cierre de la
 *   pestaña. El backend no expone cookies `httpOnly`, así que no hay una vía
 *   más segura disponible (ver README §Autenticación).
 */

const REFRESH_TOKEN_KEY = 'presto.refresh_token'

let accessToken: string | null = null

/** Devuelve el access token de la sesión en memoria. */
export function getAccessToken(): string | null {
  return accessToken
}

/** Guarda (o borra) el access token en memoria. */
export function setAccessToken(token: string | null): void {
  accessToken = token
}

/** Devuelve el refresh token guardado en la pestaña. */
export function getRefreshToken(): string | null {
  try {
    return window.sessionStorage.getItem(REFRESH_TOKEN_KEY)
  } catch {
    return null
  }
}

/** Guarda (o borra) el refresh token en la pestaña. */
export function setRefreshToken(token: string | null): void {
  try {
    if (token === null) {
      window.sessionStorage.removeItem(REFRESH_TOKEN_KEY)
      return
    }
    window.sessionStorage.setItem(REFRESH_TOKEN_KEY, token)
  } catch {
    // Si el navegador no deja usar sessionStorage, la sesión vive solo en
    // memoria: la app sigue funcionando, pero hay que volver a iniciar sesión
    // al recargar.
  }
}

/** Guarda los dos tokens de una sesión nueva. */
export function setSession(access: string, refresh: string): void {
  setAccessToken(access)
  setRefreshToken(refresh)
}

/** Borra la sesión: la app vuelve al estado anónimo. */
export function clearSession(): void {
  setAccessToken(null)
  setRefreshToken(null)
}
