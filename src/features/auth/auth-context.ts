import { createContext, useContext } from 'react'

import type { ApiClient } from '../../lib/api/client'
import type { User } from '../../lib/api/types'

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

export interface AuthContextValue {
  /** Estado de la sesión: cargando, con sesión o sin sesión. */
  status: AuthStatus
  /** El usuario de la sesión, si la hay. */
  user: User | null
  /** Cliente de la API ya configurado con la sesión. */
  client: ApiClient
  /** Inicia sesión. */
  login: (email: string, password: string) => Promise<void>
  /** Registra una cuenta e inicia sesión. */
  register: (email: string, password: string) => Promise<void>
  /** Cierra la sesión. */
  logout: () => void
  /** Renueva el access token. Devuelve el token nuevo o `null`. */
  refreshAccessToken: () => Promise<string | null>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

/** Devuelve el estado de la sesión. */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth se tiene que usar dentro de <AuthProvider>.')
  }
  return context
}

/** Devuelve el cliente de la API configurado con la sesión. */
export function useApiClient(): ApiClient {
  return useAuth().client
}
