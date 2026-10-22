import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiPaths } from '../../lib/config'
import { queryKeys } from '../../lib/query/keys'
import type {
  InvestmentProduct,
  OpenPositionRequest,
  Paginated,
  Position,
  PositionDetail,
} from '../../lib/api/types'
import { useApiClient } from '../auth/auth-context'

/**
 * Productos de inversión disponibles.
 *
 * El esquema los declara como un array, pero el backend los pagina: la
 * respuesta real es el sobre con `results`.
 */
export function useInvestmentProducts() {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.investmentProducts,
    queryFn: () => client.get<Paginated<InvestmentProduct>>(apiPaths.investmentProducts),
  })
}

/** Posiciones de inversión del usuario. */
export function usePositions() {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.positions,
    queryFn: () => client.get<Paginated<Position>>(apiPaths.positions),
  })
}

/**
 * Posiciones del usuario con el detalle de cada producto.
 *
 * La lista de posiciones no trae la moneda (solo el id del producto): hace
 * falta el detalle para saber en qué moneda está cada posición.
 *
 * @returns las posiciones con su producto y el estado de carga.
 */
export function usePositionsWithDetails() {
  const client = useApiClient()
  const positions = usePositions()

  const details = useQueries({
    queries: (positions.data?.results ?? []).map((position) => ({
      queryKey: queryKeys.position(position.id),
      queryFn: () => client.get<PositionDetail>(apiPaths.position(position.id)),
    })),
  })

  const items = (positions.data?.results ?? []).map((position, index) => ({
    position,
    detail: details[index]?.data,
  }))

  return {
    items,
    isLoading: positions.isLoading || details.some((result) => result.isLoading),
    isError: positions.isError || details.some((result) => result.isError),
    error: positions.error ?? details.find((result) => result.error)?.error,
    refetch: () => {
      void positions.refetch()
      details.forEach((result) => void result.refetch())
    },
  }
}

/** Abre una posición de inversión a plazo fijo. */
export function useOpenPosition() {
  const client = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      payload,
      idempotencyKey,
    }: {
      payload: OpenPositionRequest
      idempotencyKey: string
    }) =>
      client.post<Position>(apiPaths.positions, payload, {
        headers: { 'Idempotency-Key': idempotencyKey },
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.positions })
      void queryClient.invalidateQueries({ queryKey: queryKeys.accounts })
    },
  })
}
