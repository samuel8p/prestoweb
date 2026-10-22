import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiPaths } from '../../lib/config'
import { queryKeys } from '../../lib/query/keys'
import type {
  Budget,
  BudgetStatus,
  Category,
  CreateBudgetRequest,
  CreateCategoryRequest,
  CreateExpenseRequest,
  Expense,
  Paginated,
} from '../../lib/api/types'
import { useApiClient } from '../auth/auth-context'

/** Categorías de gasto del usuario. */
export function useCategories() {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.categories,
    queryFn: () => client.get<Paginated<Category>>(apiPaths.categories),
  })
}

/** Crea una categoría de gasto. */
export function useCreateCategory() {
  const client = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateCategoryRequest) =>
      client.post<Category>(apiPaths.categories, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.categories })
    },
  })
}

/** Renombra una categoría de gasto. */
export function useRenameCategory() {
  const client = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      client.patch<Category>(apiPaths.category(id), { name }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.categories })
    },
  })
}

/** Presupuestos mensuales del usuario. */
export function useBudgets() {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.budgets,
    queryFn: () => client.get<Paginated<Budget>>(apiPaths.budgets),
  })
}

/** Crea un presupuesto mensual. */
export function useCreateBudget() {
  const client = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateBudgetRequest) => client.post<Budget>(apiPaths.budgets, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.budgets })
    },
  })
}

/**
 * Estado de gasto de cada presupuesto del período actual.
 *
 * El backend expone el estado de un presupuesto por endpoint: se consultan
 * todos en paralelo.
 */
export function useBudgetStatuses(budgetIds: string[]) {
  const client = useApiClient()

  const results = useQueries({
    queries: budgetIds.map((id) => ({
      queryKey: queryKeys.budgetStatus(id),
      queryFn: () => client.get<BudgetStatus>(apiPaths.budgetStatus(id)),
    })),
  })

  const byBudget = new Map<string, BudgetStatus>()
  results.forEach((result) => {
    if (result.data) {
      byBudget.set(result.data.budget_id, result.data)
    }
  })

  return {
    byBudget,
    isLoading: results.some((result) => result.isLoading),
    isError: results.some((result) => result.isError),
  }
}

/** Gastos categorizados del usuario. */
export function useExpenses() {
  const client = useApiClient()

  return useQuery({
    queryKey: queryKeys.expenses,
    queryFn: () => client.get<Paginated<Expense>>(apiPaths.expenses),
  })
}

/** Categoriza un movimiento del ledger como gasto. */
export function useCategorizeMovement() {
  const client = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateExpenseRequest) => client.post<Expense>(apiPaths.expenses, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.expenses })
      void queryClient.invalidateQueries({ queryKey: queryKeys.budgets })
    },
  })
}
