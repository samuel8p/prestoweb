import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import { ApiClient } from '../../lib/api/client'
import { API_BASE_URL, apiPaths } from '../../lib/config'
import type { User } from '../../lib/api/types'
import { loginRequest, refreshRequest, registerRequest } from './api'
import { AuthContext } from './auth-context'
import type { AuthContextValue, AuthStatus } from './auth-context'
import { refreshSession } from './refreshSession'
import { clearSession, getAccessToken, getRefreshToken, setSession } from './tokenStore'

export interface AuthProviderProps {
  children: ReactNode
  /** Cliente ya construido. Se usa en los tests. */
  client?: ApiClient
}

/**
 * Proveedor de la sesión.
 *
 * Al arrancar, si hay un refresh token en la pestaña, renueva el access token
 * y recupera el usuario. Si no hay o la renovación falla, la app queda
 * como anónima.
 */
export function AuthProvider({ children, client: providedClient }: AuthProviderProps) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<User | null>(null)

  const client = useMemo(
    () =>
      providedClient ??
      new ApiClient({
        baseUrl: API_BASE_URL,
        getAccessToken,
        refreshAccessToken: refreshSession,
        onSessionExpired: () => {
          clearSession()
          setUser(null)
          setStatus('anonymous')
        },
      }),
    [providedClient],
  )

  useEffect(() => {
    let cancelled = false

    async function restoreSession() {
      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        if (!cancelled) {
          setStatus('anonymous')
        }
        return
      }

      try {
        const tokens = await refreshRequest(refreshToken)
        setSession(tokens.access, tokens.refresh)
        const profile = await client.get<User>(apiPaths.me)
        if (!cancelled) {
          setUser(profile)
          setStatus('authenticated')
        }
      } catch {
        clearSession()
        if (!cancelled) {
          setStatus('anonymous')
        }
      }
    }

    void restoreSession()

    return () => {
      cancelled = true
    }
  }, [client])

  const login = useCallback(async (email: string, password: string) => {
    const response = await loginRequest(email, password)
    setSession(response.access, response.refresh)
    setUser(response.user)
    setStatus('authenticated')
  }, [])

  const register = useCallback(async (email: string, password: string) => {
    await registerRequest(email, password)
    const response = await loginRequest(email, password)
    setSession(response.access, response.refresh)
    setUser(response.user)
    setStatus('authenticated')
  }, [])

  const logout = useCallback(() => {
    clearSession()
    setUser(null)
    setStatus('anonymous')
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, client, login, register, logout, refreshAccessToken: refreshSession }),
    [status, user, client, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
