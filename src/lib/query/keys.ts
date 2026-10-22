/**
 * Claves de las consultas de TanStack Query.
 *
 * Centralizarlas evita que dos pantallas pidan lo mismo con claves distintas
 * y que la caché se invaliden mal.
 */
export const queryKeys = {
  meta: ['meta'] as const,
  me: ['auth', 'me'] as const,
  kyc: ['kyc'] as const,
  accounts: ['ledger', 'accounts'] as const,
  accountBalance: (id: string) => ['ledger', 'accounts', id, 'balance'] as const,
  transactions: ['ledger', 'transactions'] as const,
  offers: ['offers'] as const,
  offer: (id: string) => ['offers', id] as const,
  matchingOffers: (filters: Record<string, unknown>) => ['matching', 'offers', filters] as const,
  comparisons: ['matching', 'comparisons'] as const,
  loans: ['loans'] as const,
  loan: (id: string) => ['loans', id] as const,
  investmentProducts: ['investments', 'products'] as const,
  positions: ['investments', 'positions'] as const,
  position: (id: string) => ['investments', 'positions', id] as const,
  budgets: ['budgets'] as const,
  budget: (id: string) => ['budgets', id] as const,
  budgetStatus: (id: string) => ['budgets', id, 'status'] as const,
  categories: ['budgets', 'categories'] as const,
  category: (id: string) => ['budgets', 'categories', id] as const,
  expenses: ['budgets', 'expenses'] as const,
  reportSpending: (params: Record<string, unknown>) => ['reports', 'spending', params] as const,
  reportLoans: (params: Record<string, unknown>) => ['reports', 'loans', params] as const,
  reportInvestments: (params: Record<string, unknown>) =>
    ['reports', 'investments', params] as const,
  reportMovements: (params: Record<string, unknown>) => ['reports', 'movements', params] as const,
  notifications: ['notifications'] as const,
  notificationPreferences: ['notifications', 'preferences'] as const,
}
