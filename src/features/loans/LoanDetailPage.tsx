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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/Table'
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
        <Link to="/prestamos" className="text-[13px] font-medium text-brand-700 hover:underline">
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
        secondaryActions={
          <Link to="/prestamos">
            <Button variant="secondary" icon="chevronRight" className="rotate-180">
              Volver
            </Button>
          </Link>
        }
      />

      {/* Condiciones */}
      <Card>
        <CardHeader title="Condiciones" icon="loan" />
        <dl className="grid gap-5 px-5 py-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="text-[13px] text-slate-500">Capital</dt>
            <dd className="mt-1 text-lg font-semibold text-slate-900 tabular">
              <MoneyAmount value={detail.principal} currency={currency} />
            </dd>
          </div>
          <div>
            <dt className="text-[13px] text-slate-500">Tasa anual</dt>
            <dd className="mt-1 text-lg font-semibold text-slate-900">
              {formatRate(detail.interest_rate)}
            </dd>
          </div>
          <div>
            <dt className="text-[13px] text-slate-500">Plazo</dt>
            <dd className="mt-1 text-lg font-semibold text-slate-900">
              {detail.term_months} meses
            </dd>
          </div>
          <div>
            <dt className="text-[13px] text-slate-500">Estado</dt>
            <dd className="mt-1.5">
              <Badge tone={STATUS_TONE[detail.status] ?? 'neutral'} dot>
                {STATUS_LABEL[detail.status] ?? detail.status}
              </Badge>
            </dd>
          </div>
        </dl>
        <p className="border-t border-line px-5 py-3 text-xs text-slate-500">
          Las condiciones quedan congeladas en un snapshot: editar la oferta no cambia este
          préstamo.
        </p>
      </Card>

      {actionError ? <Alert tone="danger">{actionError}</Alert> : null}

      {/* Cuotas */}
      <Card>
        <CardHeader
          title="Cuotas"
          description={`${installments.length} cuotas en total.`}
          icon="calendar"
        />

        {installments.length === 0 ? (
          <EmptyState title="Este préstamo no tiene cuotas cargadas." icon="calendar" />
        ) : (
          <Table>
            <TableHead>
              <TableHeader>Cuota</TableHeader>
              <TableHeader>Vencimiento</TableHeader>
              <TableHeader align="right">Capital</TableHeader>
              <TableHeader align="right">Interés</TableHeader>
              <TableHeader align="right">Total</TableHeader>
              <TableHeader align="right">Estado</TableHeader>
            </TableHead>
            <TableBody>
              {installments.map((installment) => (
                <TableRow key={installment.id}>
                  <TableCell className="font-medium text-slate-900 tabular">
                    {installment.number}
                  </TableCell>
                  <TableCell>
                    {formatDate(installment.due_date)}
                    {installment.paid_at ? (
                      <span className="block text-xs text-slate-400">
                        Pagada el {formatDate(installment.paid_at)}
                      </span>
                    ) : null}
                  </TableCell>
                  <TableCell align="right" className="tabular">
                    <MoneyAmount value={installment.principal_amount} currency={currency} />
                  </TableCell>
                  <TableCell align="right" className="tabular">
                    <MoneyAmount value={installment.interest_amount} currency={currency} />
                  </TableCell>
                  <TableCell align="right" className="font-semibold text-slate-900 tabular">
                    <MoneyAmount value={installment.amount} currency={currency} />
                  </TableCell>
                  <TableCell align="right">
                    <div className="flex flex-col items-end gap-2">
                      <Badge tone={INSTALLMENT_TONE[installment.status] ?? 'neutral'} dot>
                        {INSTALLMENT_LABEL[installment.status] ?? installment.status}
                      </Badge>
                      {isBorrower && installment.status !== 'paid' ? (
                        <Button
                          size="sm"
                          loading={payInstallment.isPending}
                          onClick={() => void handlePay(installment)}
                        >
                          Pagar
                        </Button>
                      ) : null}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>
    </div>
  )
}
