import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Alert } from '../../components/ui/Alert'
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
import type { Installment } from '../../lib/api/types'
import { useAuth } from '../auth/auth-context'
import { useLoan, usePayInstallment } from './api'

const INSTALLMENT_TONE = {
  pending: 'warning',
  paid: 'success',
  overdue: 'danger',
} as const

const INSTALLMENT_LABEL = {
  pending: 'Pendiente',
  paid: 'Pagada',
  overdue: 'Vencida',
} as const

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

/** Detalle de un préstamo con su cronograma de cuotas. */
export function LoanDetailPage() {
  const { loanId } = useParams<{ loanId: string }>()
  const { user } = useAuth()
  const loan = useLoan(loanId)
  const payInstallment = usePayInstallment(loanId ?? '')
  const [actionError, setActionError] = useState<string | null>(null)

  async function handlePay(installment: Installment) {
    setActionError(null)
    try {
      await payInstallment.mutateAsync(installment.number)
    } catch (error) {
      setActionError(describeError(error).message)
    }
  }

  if (loan.isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Cargando el préstamo" />
      </div>
    )
  }

  if (loan.isError) {
    return (
      <div className="flex flex-col gap-4">
        <ErrorState
          message={describeError(loan.error).message}
          onRetry={() => void loan.refetch()}
        />
        <Link to="/prestamos" className="text-sm font-medium text-brand-700 hover:underline">
          Volver a mis préstamos
        </Link>
      </div>
    )
  }

  const detail = loan.data
  if (!detail) {
    return null
  }

  const currency = detail.currency === 'USD' ? 'USD' : 'ARS'
  const isBorrower = detail.borrower_user_id === user?.id
  const installments = detail.installments

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Detalle del préstamo"
        description={`Aceptado el ${formatDate(detail.accepted_at)}`}
        action={
          <Link to="/prestamos">
            <Button variant="secondary">Volver</Button>
          </Link>
        }
      />

      <Card>
        <CardHeader title="Condiciones" />
        <dl className="grid gap-4 px-4 py-4 text-sm sm:grid-cols-2 lg:grid-cols-4 sm:px-5">
          <div>
            <dt className="text-slate-500">Capital</dt>
            <dd className="font-medium text-slate-900">
              <MoneyAmount value={detail.principal} currency={currency} />
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Tasa anual</dt>
            <dd className="font-medium text-slate-900">{formatRate(detail.interest_rate)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Plazo</dt>
            <dd className="font-medium text-slate-900">{detail.term_months} meses</dd>
          </div>
          <div>
            <dt className="text-slate-500">Estado</dt>
            <dd className="mt-1">
              <Badge tone={STATUS_TONE[detail.status] ?? 'neutral'}>
                {STATUS_LABEL[detail.status] ?? detail.status}
              </Badge>
            </dd>
          </div>
        </dl>
        <p className="px-4 pb-4 text-xs text-slate-500 sm:px-5">
          Las condiciones quedan congeladas en un snapshot: editar la oferta no cambia este
          préstamo.
        </p>
      </Card>

      {actionError ? <Alert tone="danger">{actionError}</Alert> : null}

      <Card>
        <CardHeader title="Cuotas" description={`${installments.length} cuotas en total.`} />

        {installments.length === 0 ? (
          <EmptyState title="Este préstamo no tiene cuotas cargadas." />
        ) : (
          <ul className="divide-y divide-slate-100">
            {installments.map((installment) => (
              <li
                key={installment.id}
                className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-5"
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-medium text-slate-900">Cuota {installment.number}</p>
                    <Badge tone={INSTALLMENT_TONE[installment.status] ?? 'neutral'}>
                      {INSTALLMENT_LABEL[installment.status] ?? installment.status}
                    </Badge>
                  </div>
                  <p className="mt-0.5 text-xs text-slate-500">
                    Vence el {formatDate(installment.due_date)}
                    {installment.paid_at ? ` · pagada el ${formatDate(installment.paid_at)}` : ''}
                  </p>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right text-xs text-slate-500">
                    <p>
                      Capital{' '}
                      <MoneyAmount value={installment.principal_amount} currency={currency} />
                    </p>
                    <p>
                      Interés{' '}
                      <MoneyAmount value={installment.interest_amount} currency={currency} />
                    </p>
                  </div>

                  <div className="text-right">
                    <p className="text-sm font-semibold text-slate-900">
                      <MoneyAmount value={installment.amount} currency={currency} />
                    </p>
                    {isBorrower && installment.status !== 'paid' ? (
                      <Button
                        size="sm"
                        className="mt-1"
                        loading={payInstallment.isPending}
                        onClick={() => void handlePay(installment)}
                      >
                        Pagar
                      </Button>
                    ) : null}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
