import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiPaths } from '../../lib/config'
import { queryKeys } from '../../lib/query/keys'
import type {
  AcceptOfferRequest,
  Installment,
  Loan,
  LoanDetail,
  Paginated,
} from '../../lib/api/types'
import { useApiClient } from '../auth/auth-context'

/** Préstamos del usuario, como prestatario y como prestamista. */
export function useLoans() {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.loans,
    queryFn: () => client.get<Paginated<Loan>>(apiPaths.loans),
  })
}

/** Detalle de un préstamo, con su snapshot y sus cuotas. */
export function useLoan(loanId: string | undefined) {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.loan(loanId ?? ''),
    queryFn: () => client.get<LoanDetail>(apiPaths.loan(loanId!)),
    enabled: Boolean(loanId),
  })
}

/** Acepta una oferta y recibe el préstamo. */
export function useAcceptOffer() {
  const client = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ offerId, idempotencyKey }: { offerId: string; idempotencyKey: string }) =>
      client.post<LoanDetail>(apiPaths.loans, { offer_id: offerId } satisfies AcceptOfferRequest, {
        headers: { 'Idempotency-Key': idempotencyKey },
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.loans })
      void queryClient.invalidateQueries({ queryKey: queryKeys.offers })
      void queryClient.invalidateQueries({ queryKey: queryKeys.accounts })
    },
  })
}

/** Paga una cuota del préstamo. */
export function usePayInstallment(loanId: string) {
  const client = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (number: number) =>
      client.post<Installment>(apiPaths.payInstallment(loanId, number)),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.loan(loanId) })
      void queryClient.invalidateQueries({ queryKey: queryKeys.loans })
      void queryClient.invalidateQueries({ queryKey: queryKeys.accounts })
    },
  })
}
