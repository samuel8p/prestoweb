import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiPaths } from '../../lib/config'
import { queryKeys } from '../../lib/query/keys'
import type {
  CompareOffersRequest,
  CreateOfferRequest,
  Offer,
  OfferComparison,
  OfferMatch,
  Paginated,
} from '../../lib/api/types'
import { useApiClient } from '../auth/auth-context'

export interface OfferFilters {
  currency?: string
  amount_min?: string
  amount_max?: string
  max_rate?: string
  term_months?: number
  ordering?: string
}

/** Ofertas activas del marketplace, con los filtros de la búsqueda. */
export function useMatchingOffers(filters: OfferFilters) {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.matchingOffers(filters),
    queryFn: () =>
      client.get<Paginated<OfferMatch>>(apiPaths.matchingOffers, {
        query: {
          currency: filters.currency,
          amount_min: filters.amount_min,
          amount_max: filters.amount_max,
          max_rate: filters.max_rate,
          term_months: filters.term_months,
          ordering: filters.ordering,
        },
      }),
  })
}

/** Ofertas publicadas por el usuario. */
export function useMyOffers() {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.offers,
    queryFn: () => client.get<Paginated<Offer>>(apiPaths.offers),
  })
}

/** Publica una oferta de préstamo. */
export function useCreateOffer() {
  const client = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateOfferRequest) => client.post<Offer>(apiPaths.offers, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.offers })
    },
  })
}

/** Compara dos o más ofertas. */
export function useCompareOffers() {
  const client = useApiClient()

  return useMutation({
    mutationFn: (payload: CompareOffersRequest) =>
      client.post<OfferComparison[]>(apiPaths.comparisons, payload),
  })
}
