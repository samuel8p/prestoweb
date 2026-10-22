import { describe, expect, it } from 'vitest'

import { clearSession, getAccessToken, getRefreshToken, setSession } from './tokenStore'

describe('tokenStore', () => {
  it('guarda el access token solo en memoria', () => {
    setSession('access-1', 'refresh-1')

    expect(getAccessToken()).toBe('access-1')
    // El access token no queda escrito en el almacenamiento de la pestaña.
    expect(Object.values(window.sessionStorage)).not.toContain('access-1')
    expect(window.localStorage.getItem('presto.access_token')).toBeNull()
  })

  it('guarda el refresh token en la pestaña', () => {
    setSession('access-1', 'refresh-1')

    expect(getRefreshToken()).toBe('refresh-1')
  })

  it('borra los dos tokens al cerrar la sesión', () => {
    setSession('access-1', 'refresh-1')
    clearSession()

    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
  })
})
