import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiPaths } from '../../lib/config'
import { postPublic } from '../../lib/api/http'
import type { LoginResponse, User } from '../../lib/api/types'
import { useApiClient } from './auth-context'

/** Respuesta del refresh: el backend rota los dos tokens. */
export interface RefreshResponse {
  access: string
  refresh: string
}

/**
 * Inicia sesión.
 *
 * @param email - email de la cuenta.
 * @param password - contraseña.
 * @returns los tokens y los datos del usuario.
 */
export function loginRequest(email: string, password: string): Promise<LoginResponse> {
  return postPublic<LoginResponse>(apiPaths.login, { email, password })
}

/**
 * Registra una cuenta nueva.
 *
 * @param email - email de la cuenta.
 * @param password - contraseña.
 * @returns los datos del usuario creado.
 */
export function registerRequest(email: string, password: string): Promise<User> {
  return postPublic<User>(apiPaths.register, { email, password })
}

/**
 * Renueva el access token rotando el refresh token.
 *
 * @param refresh - el refresh token vigente.
 * @returns los tokens nuevos.
 */
export function refreshRequest(refresh: string): Promise<RefreshResponse> {
  return postPublic<RefreshResponse>(apiPaths.refresh, { refresh })
}

/** El alias público del usuario (null si todavía no se puso uno). */
export function useMyAlias() {
  const client = useApiClient()

  return useQuery({
    queryKey: ['identity', 'alias'],
    queryFn: () => client.get<{ alias: string | null }>(apiPaths.myAlias),
  })
}

/** Pone o cambia el alias público del usuario. */
export function useSetAlias() {
  const client = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (alias: string) => client.put<{ alias: string }>(apiPaths.myAlias, { alias }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['identity', 'alias'] })
    },
  })
}
