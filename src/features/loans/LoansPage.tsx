import { Link } from 'react-router-dom'

import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card, CardHeader } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import { SkeletonRows } from '../../components/ui/Skeleton'
import { describeError } from '../../lib/api/errors'
import { formatDate, formatRate } from '../../lib/money/format'
import { useAuth } from '../auth/auth-context'
import { useLoans } from './api'

const STATUS_TONE = {
  active: 'success',
  paid: 'info',
  defaulted: 'danger',
} as const

const STATUS_LABEL = {
  active: 'Activo',
  paid: 'Pagado',
  defaulted: 'En mora',
} as const

/** Préstamos del usuario, como prestatario y como prestamista. */
export function LoansPage() {
  const { user } = useAuth()
  const loans = useLoans()

  const items = loans.data?.results ?? []

  return (
    <div className="flex animate-fade-up flex-col gap-6">
      <Card>
        <CardHeader title="Mis préstamos" icon="loan" />

        {loans.isLoading ? <SkeletonRows rows={3} columns={3} /> : null}

        {loans.isError ? (
          <div className="px-5 py-4">
            <ErrorState
              message={describeError(loans.error).message}
              onRetry={() => void loans.refetch()}
            />
          </div>
        ) : null}

        {!loans.isLoading && !loans.isError && items.length === 0 ? (
          <EmptyState
            title="Todavía no tenés préstamos"
            description="Aceptá una oferta del marketplace para recibir tu primer préstamo."
            action={
              <Link to="/ofertas">
                <Button size="sm">Ver ofertas</Button>
              </Link>
            }
          />
        ) : null}

        <ul className="stagger divide-y divide-line">
          {items.map((loan) => {
            const asBorrower = loan.borrower_user_id === user?.id
            const currency = loan.currency === 'USD' ? 'USD' : 'ARS'

            return (
              <li
                key={loan.id}
                className="flex flex-wrap items-center justify-between gap-4 px-5 py-4"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-base font-semibold text-ink tabular">
                      <MoneyAmount value={loan.principal} currency={currency} />
                    </p>
                    <Badge tone={asBorrower ? 'info' : 'neutral'}>
                      {asBorrower ? 'Como prestatario' : 'Como prestamista'}
                    </Badge>
                    <Badge tone={STATUS_TONE[loan.status] ?? 'neutral'} dot>
                      {STATUS_LABEL[loan.status] ?? loan.status}
                    </Badge>
                  </div>
                  <p className="mt-1 text-[13px] text-ink-muted">
                    {formatRate(loan.interest_rate)} anual · {loan.term_months} meses · aceptado el{' '}
                    {formatDate(loan.accepted_at)}
                  </p>
                </div>

                <Link to={`/prestamos/${loan.id}`} className="shrink-0">
                  <Button size="sm" variant="secondary" iconRight="chevronRight">
                    Ver cuotas
                  </Button>
                </Link>
              </li>
            )
          })}
        </ul>
      </Card>
    </div>
  )
}
