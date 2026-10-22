/**
 * Configuración de la aplicación leída del entorno.
 *
 * La URL de la API es lo único configurable: no hay secretos ni tokens en el
 * repo. `VITE_API_URL` viene de `.env` (ver `.env.example`).
 */
const DEFAULT_API_URL = 'http://127.0.0.1:8000'

function readApiUrl(): string {
  const fromEnv = import.meta.env.VITE_API_URL
  const url = typeof fromEnv === 'string' && fromEnv.trim() ? fromEnv.trim() : DEFAULT_API_URL
  return url.replace(/\/+$/, '')
}

export const API_BASE_URL = readApiUrl()

/** Rutas de la API. */
export const apiPaths = {
  meta: '/api/v1/meta/',
  login: '/api/v1/auth/login/',
  register: '/api/v1/auth/register/',
  refresh: '/api/v1/auth/token/refresh/',
  me: '/api/v1/auth/me/',
  kyc: '/api/v1/kyc/',
  kycDetail: (id: string) => `/api/v1/kyc/${id}/`,
  accounts: '/api/v1/ledger/accounts/',
  accountBalance: (id: string) => `/api/v1/ledger/accounts/${id}/balance/`,
  transactions: '/api/v1/ledger/transactions/',
  transaction: (id: string) => `/api/v1/ledger/transactions/${id}/`,
  offers: '/api/v1/offers/',
  offer: (id: string) => `/api/v1/offers/${id}/`,
  matchingOffers: '/api/v1/matching/offers/',
  comparisons: '/api/v1/matching/comparisons/',
  loans: '/api/v1/loans/',
  loan: (id: string) => `/api/v1/loans/${id}/`,
  payInstallment: (loanId: string, number: number) =>
    `/api/v1/loans/${loanId}/installments/${number}/pay/`,
  investmentProducts: '/api/v1/investments/products/',
  positions: '/api/v1/investments/positions/',
  position: (id: string) => `/api/v1/investments/positions/${id}/`,
  budgets: '/api/v1/budgets/',
  budget: (id: string) => `/api/v1/budgets/${id}/`,
  budgetStatus: (id: string) => `/api/v1/budgets/${id}/status/`,
  categories: '/api/v1/budgets/categories/',
  category: (id: string) => `/api/v1/budgets/categories/${id}/`,
  expenses: '/api/v1/budgets/expenses/',
  reportSpending: '/api/v1/reports/spending/',
  reportLoans: '/api/v1/reports/loans/',
  reportInvestments: '/api/v1/reports/investments/',
  reportMovements: '/api/v1/reports/movements/',
  notifications: '/api/v1/notifications/',
  notificationPreferences: '/api/v1/notifications/preferences/',
} as const
