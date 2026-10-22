import { useQuery } from '@tanstack/react-query'

import { apiPaths } from '../../lib/config'
import { queryKeys } from '../../lib/query/keys'
import type { Meta } from '../../lib/api/types'
import { useApiClient } from '../auth/auth-context'

/**
 * Consulta el modo de la instancia.
 *
 * El endpoint es público. Si falla, la app sigue funcionando: `meta` queda en
 * `null` y no se muestra ningún cartel.
 */
export function useMeta() {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.meta,
    queryFn: () => client.get<Meta>(apiPaths.meta, { auth: false }),
    staleTime: 5 * 60_000,
    retry: false,
  })
}
