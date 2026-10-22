import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiPaths } from '../../lib/config'
import { queryKeys } from '../../lib/query/keys'
import type {
  Account,
  Balance,
  CreateAccountRequest,
  CreateTransactionRequest,
  LedgerTransaction,
  Paginated,
} from '../../lib/api/types'
import { useApiClient } from '../auth/auth-context'

/** Billeteras del usuario (una por moneda). */
export function useAccounts() {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.accounts,
    queryFn: () => client.get<Paginated<Account>>(apiPaths.accounts),
  })
}

/** Saldo de una cuenta propia. */
export function useAccountBalance(accountId: string | undefined) {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.accountBalance(accountId ?? ''),
    queryFn: () => client.get<Balance>(apiPaths.accountBalance(accountId!)),
    enabled: Boolean(accountId),
  })
}

/** Crea la billetera del usuario para una moneda. */
export function useCreateAccount() {
  const client = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateAccountRequest) => client.post<Account>(apiPaths.accounts, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.accounts })
    },
  })
}

/** Crea un movimiento (depósito, retiro o transferencia). */
export function useCreateTransaction() {
  const client = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      payload,
      idempotencyKey,
    }: {
      payload: CreateTransactionRequest
      idempotencyKey: string
    }) =>
      client.post<LedgerTransaction>(apiPaths.transactions, payload, {
        headers: { 'Idempotency-Key': idempotencyKey },
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.accounts })
    },
  })
}
