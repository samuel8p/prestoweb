import { Link } from 'react-router-dom'

import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card, CardHeader } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
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
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Préstamos"
        description="Los préstamos que tomaste y los que vos prestaste."
        action={
          <Link to="/ofertas">
            <Button variant="secondary">Buscar ofertas</Button>
          </Link>
        }
      />

      <Card>
        <CardHeader title="Mis préstamos" />

        {loans.isLoading ? (
          <div className="flex justify-center px-4 py-10">
            <Spinner label="Cargando los préstamos" />
          </div>
        ) : null}

        {loans.isError ? (
          <div className="px-4 py-4">
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

        <ul className="divide-y divide-slate-100">
          {items.map((loan) => {
            const asBorrower = loan.borrower_user_id === user?.id
            return (
              <li
                key={loan.id}
                className="flex flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-5"
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-medium text-slate-900">
                      <MoneyAmount
                        value={loan.principal}
                        currency={loan.currency === 'USD' ? 'USD' : 'ARS'}
                      />
                    </p>
                    <Badge tone={asBorrower ? 'info' : 'neutral'}>
                      {asBorrower ? 'Como prestatario' : 'Como prestamista'}
                    </Badge>
                    <Badge tone={STATUS_TONE[loan.status] ?? 'neutral'}>
                      {STATUS_LABEL[loan.status] ?? loan.status}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {formatRate(loan.interest_rate)} anual · {loan.term_months} meses · aceptado el{' '}
                    {formatDate(loan.accepted_at)}
                  </p>
                </div>

                <Link to={`/prestamos/${loan.id}`}>
                  <Button size="sm" variant="secondary">
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
