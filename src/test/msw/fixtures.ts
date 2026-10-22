import type {
  Account,
  Balance,
  Budget,
  BudgetStatus,
  Category,
  Expense,
  Installment,
  InvestmentProduct,
  KYCVerification,
  LedgerTransaction,
  Loan,
  LoanDetail,
  LoginResponse,
  Meta,
  Notification,
  NotificationPreferenceList,
  Offer,
  OfferComparison,
  OfferMatch,
  Position,
  PositionDetail,
  SpendingReport,
  User,
} from '../../lib/api/types'

export const testUser: User = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'ana@example.com',
  first_name: 'Ana',
  last_name: 'García',
}

export const testMeta: Meta = {
  mode: 'demo',
  simulated_money: true,
}

export const testLoginResponse: LoginResponse = {
  access: 'access-token',
  refresh: 'refresh-token',
  user: testUser,
}

export function createAccount(overrides: Partial<Account> = {}): Account {
  return {
    id: '22222222-2222-4222-8222-222222222222',
    user_id: testUser.id,
    currency: 'ARS',
    kind: 'user_wallet',
    balance: '1500.50',
    created_at: '2026-10-01T10:00:00Z',
    ...overrides,
  }
}

export function createUsdAccount(overrides: Partial<Account> = {}): Account {
  return createAccount({
    id: '33333333-3333-4333-8333-333333333333',
    currency: 'USD',
    balance: '250.00',
    ...overrides,
  })
}

export function createTransaction(overrides: Partial<LedgerTransaction> = {}): LedgerTransaction {
  return {
    id: '44444444-4444-4444-8444-444444444444',
    type: 'deposit',
    idempotency_key: 'dep-1',
    created_by_user_id: testUser.id,
    destination_account_id: null,
    occurred_at: '2026-10-20T12:00:00Z',
    description: 'Depósito de prueba',
    reverses: null,
    created_at: '2026-10-20T12:00:00Z',
    ...overrides,
  }
}

export function createReversedTransaction(
  overrides: Partial<LedgerTransaction> = {},
): LedgerTransaction {
  return createTransaction({
    id: '55555555-5555-4555-8555-555555555555',
    type: 'withdrawal',
    idempotency_key: 'wd-1',
    description: 'Retiro revertido',
    ...overrides,
  })
}

export function createBalance(overrides: Partial<Balance> = {}): Balance {
  return {
    account_id: '22222222-2222-4222-8222-222222222222',
    currency: 'ARS',
    balance: '1500.50',
    ...overrides,
  }
}

export function createOffer(overrides: Partial<Offer> = {}): Offer {
  return {
    id: '66666666-6666-4666-8666-666666666666',
    lender_user_id: '99999999-9999-4999-8999-999999999999',
    amount: '100000.00',
    currency: 'ARS',
    interest_rate: '24.00',
    term_months: 12,
    requirements: 'Sin requisitos',
    status: 'active',
    created_at: '2026-10-19T09:00:00Z',
    ...overrides,
  }
}

export function createOfferMatch(overrides: Partial<OfferMatch> = {}): OfferMatch {
  return {
    id: '66666666-6666-4666-8666-666666666666',
    lender_user_id: '99999999-9999-4999-8999-999999999999',
    amount: '100000.00',
    currency: 'ARS',
    interest_rate: '24.00',
    term_months: 12,
    requirements: 'Sin requisitos',
    ...overrides,
  }
}

export function createOfferComparison(overrides: Partial<OfferComparison> = {}): OfferComparison {
  return {
    id: '66666666-6666-4666-8666-666666666666',
    lender_user_id: '99999999-9999-4999-8999-999999999999',
    amount: '100000.00',
    currency: 'ARS',
    interest_rate: '24.00',
    term_months: 12,
    requirements: 'Sin requisitos',
    installment: '9640.26',
    total_interest: '15683.12',
    total_cost: '115683.12',
    ...overrides,
  }
}

export function createLoan(overrides: Partial<Loan> = {}): Loan {
  return {
    id: '77777777-7777-4777-8777-777777777777',
    borrower_user_id: testUser.id,
    lender_user_id: '99999999-9999-4999-8999-999999999999',
    offer_id: '66666666-6666-4666-8666-666666666666',
    principal: '100000.00',
    currency: 'ARS',
    interest_rate: '24.00',
    term_months: 12,
    status: 'active',
    accepted_at: '2026-10-20T15:00:00Z',
    ...overrides,
  }
}

export function createInstallment(overrides: Partial<Installment> = {}): Installment {
  return {
    id: '88888888-8888-4888-8888-888888888881',
    number: 1,
    due_date: '2026-11-20',
    principal_amount: '8000.00',
    interest_amount: '2000.00',
    amount: '10000.00',
    status: 'pending',
    paid_at: null,
    ...overrides,
  }
}

export function createLoanDetail(overrides: Partial<LoanDetail> = {}): LoanDetail {
  return {
    ...createLoan(),
    terms_snapshot: {
      id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      accepted_at: '2026-10-20T15:00:00Z',
      accepted_by_user_id: testUser.id,
      snapshot_data: { amount: '100000.00', interest_rate: '24.00', term_months: 12 },
      is_immutable: true,
    },
    installments: [createInstallment()],
    ...overrides,
  }
}

export function createInvestmentProduct(
  overrides: Partial<InvestmentProduct> = {},
): InvestmentProduct {
  return {
    id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
    type: 'fixed_term',
    currency: 'ARS',
    term_days: 90,
    annual_rate_tna: '12.00',
    min_amount: '10000.00',
    status: 'active',
    created_at: '2026-10-01T10:00:00Z',
    ...overrides,
  }
}

export function createPosition(overrides: Partial<Position> = {}): Position {
  return {
    id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
    product: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
    amount: '50000.00',
    status: 'active',
    opened_at: '2026-10-15T10:00:00Z',
    maturity_date: '2027-01-13',
    interest_amount: '1479.45',
    ...overrides,
  }
}

export function createPositionDetail(overrides: Partial<PositionDetail> = {}): PositionDetail {
  return {
    ...createPosition(),
    product_detail: createInvestmentProduct(),
    ...overrides,
  }
}

export function createCategory(overrides: Partial<Category> = {}): Category {
  return {
    id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
    name: 'Almacenamiento',
    created_at: '2026-10-10T10:00:00Z',
    ...overrides,
  }
}

export function createBudget(overrides: Partial<Budget> = {}): Budget {
  return {
    id: 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',
    category: createCategory(),
    period: 'monthly',
    limit_amount: '200000.00',
    currency: 'ARS',
    alert_threshold: 80,
    created_at: '2026-10-10T10:00:00Z',
    ...overrides,
  }
}

export function createBudgetStatus(overrides: Partial<BudgetStatus> = {}): BudgetStatus {
  return {
    budget_id: 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',
    category_id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
    period: 'monthly',
    currency: 'ARS',
    year: 2026,
    month: 10,
    limit_amount: '200000.00',
    spent_amount: '50000.00',
    remaining_amount: '150000.00',
    threshold_amount: '160000.00',
    alert_triggered: false,
    ...overrides,
  }
}

export function createExpense(overrides: Partial<Expense> = {}): Expense {
  return {
    id: 'ffffffff-ffff-4fff-8fff-ffffffffffff',
    category: createCategory(),
    ledger_transaction_id: '44444444-4444-4444-8444-444444444444',
    created_at: '2026-10-20T12:00:00Z',
    ...overrides,
  }
}

export function createNotification(overrides: Partial<Notification> = {}): Notification {
  return {
    id: '12121212-1212-4212-8212-121212121212',
    user_id: testUser.id,
    event_type: 'installment_due_soon',
    reference_id: '77777777-7777-4777-8777-777777777777',
    status: 'sent',
    created_at: '2026-10-20T08:00:00Z',
    sent_at: '2026-10-20T08:00:05Z',
    error: '',
    ...overrides,
  }
}

export function createNotificationPreferences(): NotificationPreferenceList {
  return {
    preferences: [
      { event_type: 'installment_due_soon', enabled: true },
      { event_type: 'installment_overdue', enabled: true },
      { event_type: 'investment_settled', enabled: true },
      { event_type: 'budget_alert', enabled: true },
    ],
  }
}

export function createKycVerification(overrides: Partial<KYCVerification> = {}): KYCVerification {
  return {
    id: '13131313-1313-4313-8313-131313131313',
    status: 'approved',
    requested_at: '2026-10-01T10:00:00Z',
    resolved_at: '2026-10-01T11:00:00Z',
    resolved_by_user_id: '99999999-9999-4999-8999-999999999999',
    documents: { id_document: 'dni-1234' },
    ...overrides,
  }
}

export function createSpendingReport(overrides: Partial<SpendingReport> = {}): SpendingReport {
  return {
    currency: 'ARS',
    from_date: '2026-10-01',
    to_date: '2026-10-31',
    total: '50000.00',
    categories: [
      {
        category_id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
        category_name: 'Almacenamiento',
        amount: '50000.00',
        movements: 3,
      },
    ],
    ...overrides,
  }
}
