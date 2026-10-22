import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiPaths } from '../../lib/config'
import { queryKeys } from '../../lib/query/keys'
import type { KYCVerification } from '../../lib/api/types'
import { useApiClient } from './auth-context'

/**
 * Estado de la verificación KYC del usuario.
 *
 * El backend devuelve `null` cuando el usuario todavía no pidió la
 * verificación.
 */
export function useKyc() {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.kyc,
    queryFn: () => client.get<KYCVerification | null>(apiPaths.kyc),
  })
}

/** Pide (o repite) la verificación KYC. */
export function useSubmitKyc() {
  const client = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (documents: Record<string, unknown>) =>
      client.post<KYCVerification>(apiPaths.kyc, { documents }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.kyc })
    },
  })
}
