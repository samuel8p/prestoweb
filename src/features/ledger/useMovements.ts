import { useInfiniteQuery } from '@tanstack/react-query'

import { apiPaths } from '../../lib/config'
import { queryKeys } from '../../lib/query/keys'
import type { Currency } from '../../lib/money/format'
import type { MovementReportRow, Paginated } from '../../lib/api/types'
import { useApiClient } from '../auth/auth-context'

export interface MovementFilters {
  currency: Currency
  from?: string
  to?: string
}

/**
 * Movimientos del usuario en una moneda y un rango de fechas.
 *
 * El backend expone el importe y la marca de revertido en el reporte de
 * movimientos: la lista del ledger no trae importes.
 */
export function useMovements(filters: MovementFilters) {
  const client = useApiClient()
  const { currency, from, to } = filters

  return useInfiniteQuery({
    queryKey: queryKeys.reportMovements({ currency, from, to }),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      pageParam
        ? client.get<Paginated<MovementReportRow>>(pageParam)
        : client.get<Paginated<MovementReportRow>>(apiPaths.reportMovements, {
            query: { currency, from, to, page_size: 25 },
          }),
    getNextPageParam: (lastPage) => lastPage.next ?? undefined,
  })
}
