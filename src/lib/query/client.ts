import { QueryClient } from '@tanstack/react-query'

import { ApiError } from '../api/errors'

/**
 * Crea el cliente de consultas.
 *
 * Los errores 4xx no se reintentan: si la API dice que el payload está mal o
 * que no hay permiso, repetir la misma llamada no va a cambiar la respuesta.
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: (failureCount, error) => {
          if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
            return false
          }
          return failureCount < 1
        },
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: false,
      },
    },
  })
}
