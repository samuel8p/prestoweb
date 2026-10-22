import { useQueries } from '@tanstack/react-query'

import { apiPaths } from '../../lib/config'
import { defaultReportRange } from '../../lib/dates'
import { queryKeys } from '../../lib/query/keys'
import type { MovementReportRow, Paginated } from '../../lib/api/types'
import type { Currency } from '../../lib/money/format'
import { useApiClient } from '../auth/auth-context'

/**
 * Últimos movimientos del usuario en varias monedas.
 *
 * Cada consulta es de una sola moneda (el backend no mezcla monedas) y los
 * resultados se ordenan por fecha al juntarlos.
 *
 * @param currencies - las monedas que hay que consultar.
 */
export function useRecentMovements(currencies: Currency[]) {
  const client = useApiClient()
  const { from, to } = defaultReportRange()

  const results = useQueries({
    queries: currencies.map((currency) => ({
      queryKey: queryKeys.reportMovements({ currency, from, to, recent: true }),
      queryFn: () =>
        client.get<Paginated<MovementReportRow>>(apiPaths.reportMovements, {
          query: { currency, from, to, page_size: 5 },
        }),
    })),
  })

  const seen = new Set<string>()
  const movements = results
    .flatMap((result) => result.data?.results ?? [])
    .filter((movement) => {
      if (seen.has(movement.id)) {
        return false
      }
      seen.add(movement.id)
      return true
    })
    .sort((left, right) => right.occurred_at.localeCompare(left.occurred_at))
    .slice(0, 5)

  return {
    movements,
    isLoading: results.some((result) => result.isLoading),
    isError: results.some((result) => result.isError),
    refetch: () => results.forEach((result) => void result.refetch()),
  }
}
