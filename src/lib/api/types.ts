import type { components } from './schema'

/** Todos los esquemas del backend, tal como los define `docs/openapi.yaml`. */
export type Schemas = components['schemas']

export type User = Schemas['User']
export type Account = Schemas['Account']
export type Balance = Schemas['Balance']
export type Budget = Schemas['Budget']
export type BudgetStatus = Schemas['BudgetStatus']
export type Category = Schemas['Category']
export type Expense = Schemas['Expense']
export type Installment = Schemas['Installment']
export type InstallmentStatus = Schemas['InstallmentStatusEnum']
export type InvestmentProduct = Schemas['InvestmentProduct']
export type InvestmentProductStatus = Schemas['InvestmentProductStatusEnum']
export type InvestmentsReport = Schemas['InvestmentsReport']
export type InvestmentPosition = Schemas['InvestmentPosition']
export type KYCVerification = Schemas['KYCVerification']
export type KYCVerificationStatus = Schemas['KYCVerificationStatusEnum']
export type LedgerTransaction = Schemas['LedgerTransaction']
export type LedgerTransactionType = Schemas['LedgerTransactionTypeEnum']
export type Loan = Schemas['Loan']
export type LoanDetail = Schemas['LoanDetail']
export type LoanStatus = Schemas['LoanStatusEnum']
export type LoansReport = Schemas['LoansReport']
export type LoginResponse = Schemas['LoginResponse']
export type Meta = Schemas['Meta']
export type MovementReportRow = Schemas['MovementReportRow']
export type Notification = Schemas['Notification']
export type NotificationPreference = Schemas['NotificationPreference']
export type NotificationPreferenceList = Schemas['NotificationPreferenceList']
export type NotificationStatus = Schemas['NotificationStatusEnum']
export type Offer = Schemas['Offer']
export type OfferComparison = Schemas['OfferComparison']
export type OfferMatch = Schemas['OfferMatch']
export type OfferStatus = Schemas['OfferStatusEnum']
export type OfferTermsSnapshot = Schemas['OfferTermsSnapshot']
export type Position = Schemas['Position']
export type PositionDetail = Schemas['PositionDetail']
export type PositionStatus = Schemas['PositionStatusEnum']
export type SpendingCategory = Schemas['SpendingCategory']
export type SpendingReport = Schemas['SpendingReport']
export type EventType = Schemas['EventTypeEnum']
export type Currency = Schemas['CurrencyEnum']

/** Cuerpo de `POST /api/v1/auth/login/`. */
export type LoginRequest = Schemas['Login']
/** Cuerpo de `POST /api/v1/auth/register/`. */
export type RegisterRequest = Schemas['Register']
/** Cuerpo de `PATCH /api/v1/auth/me/`. */
export type MeUpdateRequest = Schemas['PatchedMeUpdate']
/** Cuerpo de `POST /api/v1/kyc/`. */
export type KYCRequest = Schemas['KYCRequest']
/** Cuerpo de `POST /api/v1/ledger/accounts/`. */
export type CreateAccountRequest = Schemas['CreateAccount']
/** Cuerpo de `POST /api/v1/ledger/transactions/`. */
export type CreateTransactionRequest = Schemas['CreateTransaction']
/** Cuerpo de `POST /api/v1/offers/`. */
export type CreateOfferRequest = Schemas['CreateOffer']
/** Cuerpo de `PATCH /api/v1/offers/{offer_id}/`. */
export type UpdateOfferRequest = Schemas['PatchedUpdateOffer']
/** Cuerpo de `POST /api/v1/loans/`. */
export type AcceptOfferRequest = Schemas['AcceptOffer']
/** Cuerpo de `POST /api/v1/investments/positions/`. */
export type OpenPositionRequest = Schemas['OpenPosition']
/** Cuerpo de `POST /api/v1/budgets/`. */
export type CreateBudgetRequest = Schemas['CreateBudget']
/** Cuerpo de `POST /api/v1/budgets/categories/`. */
export type CreateCategoryRequest = Schemas['CreateCategory']
/** Cuerpo de `POST /api/v1/budgets/expenses/`. */
export type CreateExpenseRequest = Schemas['CreateExpense']
/** Cuerpo de `POST /api/v1/matching/comparisons/`. */
export type CompareOffersRequest = Schemas['CompareOffers']
/** Cuerpo de `PUT /api/v1/notifications/preferences/`. */
export type NotificationPreferenceRequest = Schemas['NotificationPreference']

/** Página con paginación por número (la usan casi todos los listados). */
export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/** Página con paginación por cursor (la usan los movimientos del ledger). */
export interface CursorPaginated<T> {
  next: string | null
  previous: string | null
  results: T[]
}
