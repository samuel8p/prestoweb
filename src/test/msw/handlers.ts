import { HttpResponse, http } from 'msw'
import type { HttpHandler } from 'msw'

import type {
  Account,
  Budget,
  Category,
  CreateBudgetRequest,
  CreateCategoryRequest,
  CreateExpenseRequest,
  CreateOfferRequest,
  CreateTransactionRequest,
  Expense,
  InvestmentProduct,
  InvestmentsReport,
  KYCRequest,
  KYCVerification,
  LedgerTransaction,
  LoanDetail,
  LoansReport,
  LoginRequest,
  LoginResponse,
  Meta,
  MovementReportRow,
  Notification,
  NotificationPreference,
  NotificationPreferenceList,
  Offer,
  OpenPositionRequest,
  Paginated,
  Position,
  RegisterRequest,
  User,
} from '../../lib/api/types'
import {
  createAccount,
  createBalance,
  createBudget,
  createBudgetStatus,
  createCategory,
  createExpense,
  createInvestmentProduct,
  createKycVerification,
  createLoanDetail,
  createNotification,
  createNotificationPreferences,
  createOffer,
  createOfferComparison,
  createOfferMatch,
  createPosition,
  createPositionDetail,
  createSpendingReport,
  createTransaction,
  createUsdAccount,
  testLoginResponse,
  testMeta,
  testUser,
} from './fixtures'

const API = '*/api/v1'

function paginated<T>(results: T[]): Paginated<T> {
  return { count: results.length, next: null, previous: null, results }
}

/** Estado en memoria que los handlers de MSW van mutando. */
export interface TestState {
  accounts: Account[]
  transactions: LedgerTransaction[]
  offers: Offer[]
  loans: LoanDetail[]
  positions: Position[]
  categories: Category[]
  budgets: Budget[]
  expenses: Expense[]
  notifications: Notification[]
  preferences: NotificationPreference[]
  products: InvestmentProduct[]
  kyc: KYCVerification | null
  user: User
  meta: Meta
  login: LoginResponse
}

export function createState(): TestState {
  return {
    accounts: [createAccount(), createUsdAccount()],
    transactions: [createTransaction()],
    offers: [createOffer()],
    loans: [createLoanDetail()],
    positions: [createPosition()],
    categories: [createCategory()],
    budgets: [createBudget()],
    expenses: [createExpense()],
    notifications: [createNotification()],
    preferences: createNotificationPreferences().preferences,
    products: [createInvestmentProduct()],
    kyc: createKycVerification(),
    user: testUser,
    meta: testMeta,
    login: testLoginResponse,
  }
}

export const state: TestState = createState()

export function resetState(): void {
  const fresh = createState()
  Object.assign(state, fresh)
}

function errorResponse(status: number, code: string, message: string, details = {}) {
  return HttpResponse.json({ error: { code, message, details } }, { status })
}

/**
 * Handlers de MSW con respuestas felices por defecto.
 *
 * Cada test puede pisar lo que necesite con `server.use(...)`.
 */
export const handlers: HttpHandler[] = [
  // --- meta y autenticación ---
  http.get(`${API}/meta/`, () => HttpResponse.json(state.meta)),

  http.post(`${API}/auth/login/`, async ({ request }) => {
    const body = (await request.json()) as LoginRequest
    if (body.email !== state.user.email) {
      return errorResponse(401, 'not_authenticated', 'Email o contraseña incorrectos.')
    }
    return HttpResponse.json(state.login)
  }),

  http.post(`${API}/auth/register/`, async ({ request }) => {
    const body = (await request.json()) as RegisterRequest
    if (!body.email || !body.password) {
      return errorResponse(400, 'validation_error', 'Los datos enviados no son válidos.', {
        email: ['Este campo es obligatorio.'],
      })
    }
    return HttpResponse.json(state.user, { status: 201 })
  }),

  http.post(`${API}/auth/token/refresh/`, async ({ request }) => {
    const body = (await request.json()) as { refresh?: string }
    if (!body.refresh) {
      return errorResponse(401, 'not_authenticated', 'Tu sesión expiró. Volvé a iniciar sesión.')
    }
    return HttpResponse.json({ access: 'access-token-2', refresh: 'refresh-token-2' })
  }),

  http.get(`${API}/auth/me/`, () => HttpResponse.json(state.user)),

  http.patch(`${API}/auth/me/`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    Object.assign(state.user, body)
    return HttpResponse.json(state.user)
  }),

  http.get(`${API}/kyc/`, () => HttpResponse.json(state.kyc)),

  http.post(`${API}/kyc/`, async ({ request }) => {
    const body = (await request.json()) as KYCRequest
    state.kyc = createKycVerification({ status: 'pending', documents: body.documents })
    return HttpResponse.json(state.kyc, { status: 201 })
  }),

  http.get(`${API}/kyc/:verificationId`, ({ params }) => {
    if (state.kyc?.id !== params.verificationId) {
      return errorResponse(404, 'not_found', 'No encontramos lo que estabas buscando.')
    }
    return HttpResponse.json(state.kyc)
  }),

  // --- ledger ---
  http.get(`${API}/ledger/accounts/`, () => HttpResponse.json(paginated(state.accounts))),

  http.post(`${API}/ledger/accounts/`, async ({ request }) => {
    const body = (await request.json()) as { currency: Account['currency'] }
    const account = createAccount({
      id: `wallet-${body.currency}`,
      currency: body.currency,
      balance: '0.00',
    })
    state.accounts.push(account)
    return HttpResponse.json(account, { status: 201 })
  }),

  http.get(`${API}/ledger/accounts/:accountId/balance/`, ({ params }) => {
    const account = state.accounts.find((item) => item.id === params.accountId)
    if (!account) {
      return errorResponse(404, 'not_found', 'No encontramos lo que estabas buscando.')
    }
    return HttpResponse.json(
      createBalance({
        account_id: account.id,
        currency: account.currency,
        balance: account.balance,
      }),
    )
  }),

  http.get(`${API}/ledger/transactions/`, () =>
    HttpResponse.json({ next: null, previous: null, results: state.transactions }),
  ),

  http.post(`${API}/ledger/transactions/`, async ({ request }) => {
    const idempotencyKey = request.headers.get('Idempotency-Key')
    if (!idempotencyKey) {
      return errorResponse(400, 'validation_error', 'Los datos enviados no son válidos.', {
        idempotency_key: ['El header Idempotency-Key es obligatorio.'],
      })
    }
    const body = (await request.json()) as CreateTransactionRequest
    const existing = state.transactions.find((item) => item.idempotency_key === idempotencyKey)
    if (existing) {
      return HttpResponse.json(existing)
    }
    const transaction = createTransaction({
      id: `tx-${state.transactions.length + 1}`,
      type: body.type,
      idempotency_key: idempotencyKey,
      description: body.description ?? '',
    })
    state.transactions.unshift(transaction)
    return HttpResponse.json(transaction, { status: 201 })
  }),

  http.get(`${API}/ledger/transactions/:transactionId`, ({ params }) => {
    const transaction = state.transactions.find((item) => item.id === params.transactionId)
    if (!transaction) {
      return errorResponse(404, 'not_found', 'No encontramos lo que estabas buscando.')
    }
    return HttpResponse.json(transaction)
  }),

  // --- ofertas y matching ---
  http.get(`${API}/offers/`, () => HttpResponse.json(paginated(state.offers))),

  http.post(`${API}/offers/`, async ({ request }) => {
    const body = (await request.json()) as CreateOfferRequest
    const offer = createOffer({
      id: `offer-${state.offers.length + 1}`,
      lender_user_id: state.user.id,
      amount: body.amount,
      currency: body.currency,
      interest_rate: body.interest_rate,
      term_months: body.term_months,
      requirements: body.requirements ?? '',
    })
    state.offers.push(offer)
    return HttpResponse.json(offer, { status: 201 })
  }),

  http.get(`${API}/offers/:offerId`, ({ params }) => {
    const offer = state.offers.find((item) => item.id === params.offerId)
    if (!offer) {
      return errorResponse(404, 'not_found', 'No encontramos lo que estabas buscando.')
    }
    return HttpResponse.json(offer)
  }),

  http.patch(`${API}/offers/:offerId`, async ({ request, params }) => {
    const body = (await request.json()) as Record<string, unknown>
    const offer = state.offers.find((item) => item.id === params.offerId)
    if (!offer) {
      return errorResponse(404, 'not_found', 'No encontramos lo que estabas buscando.')
    }
    Object.assign(offer, body)
    return HttpResponse.json(offer)
  }),

  http.get(`${API}/matching/offers/`, () => HttpResponse.json(paginated([createOfferMatch()]))),

  http.post(`${API}/matching/comparisons/`, async ({ request }) => {
    const body = (await request.json()) as { offer_ids: string[] }
    return HttpResponse.json(body.offer_ids.map((id) => createOfferComparison({ id })))
  }),

  // --- préstamos ---
  http.get(`${API}/loans/`, () =>
    HttpResponse.json(
      paginated(
        state.loans.map((loan) => ({
          id: loan.id,
          borrower_user_id: loan.borrower_user_id,
          lender_user_id: loan.lender_user_id,
          offer_id: loan.offer_id,
          principal: loan.principal,
          currency: loan.currency,
          interest_rate: loan.interest_rate,
          term_months: loan.term_months,
          status: loan.status,
          accepted_at: loan.accepted_at,
        })),
      ),
    ),
  ),

  http.post(`${API}/loans/`, async ({ request }) => {
    if (!request.headers.get('Idempotency-Key')) {
      return errorResponse(400, 'validation_error', 'Los datos enviados no son válidos.', {
        idempotency_key: ['El header Idempotency-Key es obligatorio.'],
      })
    }
    const body = (await request.json()) as { offer_id: string }
    const loan = createLoanDetail({ id: `loan-${state.loans.length + 1}`, offer_id: body.offer_id })
    state.loans.push(loan)
    return HttpResponse.json(loan, { status: 201 })
  }),

  http.get(`${API}/loans/:loanId`, ({ params }) => {
    const loan = state.loans.find((item) => item.id === params.loanId)
    if (!loan) {
      return errorResponse(404, 'not_found', 'No encontramos lo que estabas buscando.')
    }
    return HttpResponse.json(loan)
  }),

  http.post(`${API}/loans/:loanId/installments/:number/pay/`, ({ params }) => {
    const loan = state.loans.find((item) => item.id === params.loanId)
    if (!loan) {
      return errorResponse(404, 'not_found', 'No encontramos lo que estabas buscando.')
    }
    const number = Number(params.number)
    const index = loan.installments.findIndex((item) => item.number === number)
    if (index === -1) {
      return errorResponse(404, 'not_found', 'No encontramos lo que estabas buscando.')
    }
    const installment = {
      ...loan.installments[index]!,
      status: 'paid' as const,
      paid_at: new Date().toISOString(),
    }
    loan.installments[index] = installment
    return HttpResponse.json(installment)
  }),

  // --- inversiones ---
  http.get(`${API}/investments/products/`, () => HttpResponse.json(state.products)),

  http.get(`${API}/investments/positions/`, () => HttpResponse.json(paginated(state.positions))),

  http.post(`${API}/investments/positions/`, async ({ request }) => {
    if (!request.headers.get('Idempotency-Key')) {
      return errorResponse(400, 'validation_error', 'Los datos enviados no son válidos.', {
        idempotency_key: ['El header Idempotency-Key es obligatorio.'],
      })
    }
    const body = (await request.json()) as OpenPositionRequest
    const position = createPosition({
      id: `position-${state.positions.length + 1}`,
      product: body.product_id,
      amount: body.amount,
    })
    state.positions.push(position)
    return HttpResponse.json(position, { status: 201 })
  }),

  http.get(`${API}/investments/positions/:positionId`, ({ params }) => {
    const position = state.positions.find((item) => item.id === params.positionId)
    if (!position) {
      return errorResponse(404, 'not_found', 'No encontramos lo que estabas buscando.')
    }
    return HttpResponse.json(createPositionDetail(position))
  }),

  // --- presupuestos ---
  http.get(`${API}/budgets/`, () => HttpResponse.json(paginated(state.budgets))),

  http.post(`${API}/budgets/`, async ({ request }) => {
    const body = (await request.json()) as CreateBudgetRequest
    const budget = createBudget({
      id: `budget-${state.budgets.length + 1}`,
      category:
        state.categories.find((item) => item.id === body.category_id) ?? state.categories[0]!,
      limit_amount: body.limit_amount,
      currency: body.currency,
      alert_threshold: body.alert_threshold,
    })
    state.budgets.push(budget)
    return HttpResponse.json(budget, { status: 201 })
  }),

  http.get(`${API}/budgets/:budgetId`, ({ params }) => {
    const budget = state.budgets.find((item) => item.id === params.budgetId)
    if (!budget) {
      return errorResponse(404, 'not_found', 'No encontramos lo que estabas buscando.')
    }
    return HttpResponse.json(budget)
  }),

  http.patch(`${API}/budgets/:budgetId`, async ({ request, params }) => {
    const body = (await request.json()) as Record<string, unknown>
    const budget = state.budgets.find((item) => item.id === params.budgetId)
    if (!budget) {
      return errorResponse(404, 'not_found', 'No encontramos lo que estabas buscando.')
    }
    Object.assign(budget, body)
    return HttpResponse.json(budget)
  }),

  http.get(`${API}/budgets/:budgetId/status/`, ({ params }) => {
    const budget = state.budgets.find((item) => item.id === params.budgetId)
    if (!budget) {
      return errorResponse(404, 'not_found', 'No encontramos lo que estabas buscando.')
    }
    return HttpResponse.json(createBudgetStatus({ budget_id: budget.id }))
  }),

  http.get(`${API}/budgets/categories/`, () => HttpResponse.json(paginated(state.categories))),

  http.post(`${API}/budgets/categories/`, async ({ request }) => {
    const body = (await request.json()) as CreateCategoryRequest
    const category = createCategory({
      id: `category-${state.categories.length + 1}`,
      name: body.name,
    })
    state.categories.push(category)
    return HttpResponse.json(category, { status: 201 })
  }),

  http.get(`${API}/budgets/categories/:categoryId`, ({ params }) => {
    const category = state.categories.find((item) => item.id === params.categoryId)
    if (!category) {
      return errorResponse(404, 'not_found', 'No encontramos lo que estabas buscando.')
    }
    return HttpResponse.json(category)
  }),

  http.patch(`${API}/budgets/categories/:categoryId`, async ({ request, params }) => {
    const body = (await request.json()) as { name?: string }
    const category = state.categories.find((item) => item.id === params.categoryId)
    if (!category) {
      return errorResponse(404, 'not_found', 'No encontramos lo que estabas buscando.')
    }
    const renamed = { ...category, name: body.name ?? category.name }
    state.categories[state.categories.indexOf(category)] = renamed
    return HttpResponse.json(renamed)
  }),

  http.get(`${API}/budgets/expenses/`, () => HttpResponse.json(paginated(state.expenses))),

  http.post(`${API}/budgets/expenses/`, async ({ request }) => {
    const body = (await request.json()) as CreateExpenseRequest
    const expense = createExpense({
      id: `expense-${state.expenses.length + 1}`,
      category:
        state.categories.find((item) => item.id === body.category_id) ?? state.categories[0]!,
      ledger_transaction_id: body.ledger_transaction_id,
    })
    state.expenses.push(expense)
    return HttpResponse.json(expense, { status: 201 })
  }),

  // --- reportes ---
  http.get(`${API}/reports/spending/`, ({ request }) => {
    const url = new URL(request.url)
    if (url.searchParams.get('export') === 'csv') {
      return HttpResponse.text('category_id,category_name,amount,movements\n', {
        headers: {
          'Content-Type': 'text/csv; charset=utf-8',
          'Content-Disposition': 'attachment; filename="reporte-gasto.csv"',
        },
      })
    }
    return HttpResponse.json(createSpendingReport())
  }),

  http.get(`${API}/reports/loans/`, () =>
    HttpResponse.json({
      currency: 'ARS',
      as_borrower: {
        active_loans: 1,
        outstanding_amount: '100000.00',
        interest_amount: '15683.12',
        next_installments: [],
      },
      as_lender: {
        active_loans: 0,
        outstanding_amount: '0.00',
        interest_amount: '0.00',
        next_installments: [],
      },
    } satisfies LoansReport),
  ),

  http.get(`${API}/reports/investments/`, () =>
    HttpResponse.json({
      currency: 'ARS',
      total_invested: '50000.00',
      interest_expected: '1479.45',
      interest_earned: '0.00',
      positions: [],
    } satisfies InvestmentsReport),
  ),

  http.get(`${API}/reports/movements/`, () =>
    HttpResponse.json(
      paginated<MovementReportRow>([
        {
          id: '44444444-4444-4444-8444-444444444444',
          type: 'deposit',
          amount: '1500.50',
          currency: 'ARS',
          occurred_at: '2026-10-20T12:00:00Z',
          description: 'Depósito de prueba',
          is_reversed: false,
        },
      ]),
    ),
  ),

  // --- notificaciones ---
  http.get(`${API}/notifications/`, () => HttpResponse.json(paginated(state.notifications))),

  http.get(`${API}/notifications/preferences/`, () =>
    HttpResponse.json({ preferences: state.preferences } satisfies NotificationPreferenceList),
  ),

  http.put(`${API}/notifications/preferences/`, async ({ request }) => {
    const body = (await request.json()) as NotificationPreference
    const existing = state.preferences.find((item) => item.event_type === body.event_type)
    if (existing) {
      existing.enabled = body.enabled
    }
    return HttpResponse.json(body)
  }),
]
