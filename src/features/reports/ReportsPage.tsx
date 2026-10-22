import { useState } from 'react'

import { Alert } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card, CardHeader } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Input } from '../../components/ui/Input'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import { PageHeader } from '../../components/ui/PageHeader'
import { Select } from '../../components/ui/Select'
import { Spinner } from '../../components/ui/Spinner'
import { describeError } from '../../lib/api/errors'
import { defaultReportRange } from '../../lib/dates'
import { formatDate } from '../../lib/money/format'
import type { Currency } from '../../lib/money/format'
import {
  useInvestmentsReport,
  useLoansReport,
  useMovementsReport,
  useReportCsv,
  useSpendingReport,
} from './api'
import type { ReportKey } from './api'

type ReportTab = 'movimientos' | 'gasto' | 'prestamos' | 'inversiones'

const TABS: Array<{ id: ReportTab; label: string }> = [
  { id: 'movimientos', label: 'Movimientos' },
  { id: 'gasto', label: 'Gasto por categoría' },
  { id: 'prestamos', label: 'Préstamos' },
  { id: 'inversiones', label: 'Inversiones' },
]

const CURRENCY_OPTIONS = [
  { value: 'ARS', label: 'Pesos (ARS)' },
  { value: 'USD', label: 'Dólares (USD)' },
]

/** Reportes de solo lectura, con selector de moneda, rango y descarga CSV. */
export function ReportsPage() {
  const [tab, setTab] = useState<ReportTab>('movimientos')
  const [currency, setCurrency] = useState<Currency>('ARS')
  const [range, setRange] = useState(() => defaultReportRange())
  const [actionError, setActionError] = useState<string | null>(null)

  const rangeParams = { currency, from: range.from, to: range.to }
  const spending = useSpendingReport(rangeParams)
  const loansReport = useLoansReport(currency)
  const investments = useInvestmentsReport(currency)
  const movements = useMovementsReport(rangeParams)
  const downloadCsv = useReportCsv()

  const reportKey: ReportKey =
    tab === 'gasto'
      ? 'spending'
      : tab === 'prestamos'
        ? 'loans'
        : tab === 'inversiones'
          ? 'investments'
          : 'movements'

  async function handleDownload() {
    setActionError(null)
    try {
      await downloadCsv.mutateAsync({ report: reportKey, range: rangeParams })
    } catch (error) {
      setActionError(describeError(error).message)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Reportes"
        description="Resumenes de tu actividad, en una moneda y un rango de fechas."
        action={
          <Button
            variant="secondary"
            loading={downloadCsv.isPending}
            onClick={() => void handleDownload()}
          >
            Descargar CSV
          </Button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <Select
          label="Moneda"
          value={currency}
          options={CURRENCY_OPTIONS}
          onChange={(event) => setCurrency(event.target.value as Currency)}
        />
        <Input
          label="Desde"
          type="date"
          value={range.from}
          onChange={(event) => setRange((current) => ({ ...current, from: event.target.value }))}
        />
        <Input
          label="Hasta"
          type="date"
          value={range.to}
          onChange={(event) => setRange((current) => ({ ...current, to: event.target.value }))}
        />
      </div>

      <p className="-mt-2 text-xs text-slate-500">
        El rango máximo es de 12 meses. Los reportes de préstamos e inversiones son del período
        actual.
      </p>

      {actionError ? <Alert tone="danger">{actionError}</Alert> : null}

      <div role="tablist" aria-label="Reportes" className="flex flex-wrap gap-2">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            onClick={() => setTab(item.id)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === item.id
                ? 'bg-brand-600 text-white'
                : 'bg-white text-slate-600 border border-slate-300 hover:bg-slate-50'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === 'movimientos' ? (
        <Card>
          <CardHeader title="Movimientos del período" />
          {movements.isLoading ? (
            <div className="flex justify-center px-4 py-10">
              <Spinner label="Cargando el reporte" />
            </div>
          ) : null}
          {movements.isError ? (
            <div className="px-4 py-4">
              <ErrorState
                message={describeError(movements.error).message}
                onRetry={() => void movements.refetch()}
              />
            </div>
          ) : null}
          {!movements.isLoading &&
          !movements.isError &&
          (movements.data?.results.length ?? 0) === 0 ? (
            <EmptyState title="No hay movimientos en el período" />
          ) : null}
          <ul className="divide-y divide-slate-100">
            {(movements.data?.results ?? []).map((movement) => (
              <li
                key={movement.id}
                className="flex items-center justify-between gap-3 px-4 py-3 sm:px-5"
              >
                <div>
                  <p className="text-sm font-medium text-slate-900">{movement.type}</p>
                  <p className="text-xs text-slate-500">
                    {movement.description || 'Sin descripción'} · {formatDate(movement.occurred_at)}
                  </p>
                </div>
                <div className="text-right">
                  <MoneyAmount
                    value={movement.amount}
                    currency={movement.currency === 'USD' ? 'USD' : 'ARS'}
                    className="text-sm font-semibold text-slate-900"
                  />
                  {movement.is_reversed ? <Badge tone="danger">Revertido</Badge> : null}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {tab === 'gasto' ? (
        <Card>
          <CardHeader
            title="Gasto por categoría"
            description={`Del ${range.from} al ${range.to}.`}
          />
          {spending.isLoading ? (
            <div className="flex justify-center px-4 py-10">
              <Spinner label="Cargando el reporte" />
            </div>
          ) : null}
          {spending.isError ? (
            <div className="px-4 py-4">
              <ErrorState
                message={describeError(spending.error).message}
                onRetry={() => void spending.refetch()}
              />
            </div>
          ) : null}
          {!spending.isLoading &&
          !spending.isError &&
          (spending.data?.categories ?? []).length === 0 ? (
            <EmptyState title="No hay gastos categorizados en el período" />
          ) : null}
          <ul className="divide-y divide-slate-100">
            {(spending.data?.categories ?? []).map((category) => (
              <li
                key={category.category_id}
                className="flex items-center justify-between gap-3 px-4 py-3 sm:px-5"
              >
                <div>
                  <p className="text-sm font-medium text-slate-900">{category.category_name}</p>
                  <p className="text-xs text-slate-500">{category.movements} movimientos</p>
                </div>
                <MoneyAmount
                  value={category.amount}
                  currency={currency}
                  className="text-sm font-semibold text-slate-900"
                />
              </li>
            ))}
          </ul>
          {spending.data ? (
            <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 sm:px-5">
              <p className="text-sm font-medium text-slate-700">Total</p>
              <MoneyAmount
                value={spending.data.total}
                currency={currency}
                className="text-sm font-bold text-slate-900"
              />
            </div>
          ) : null}
        </Card>
      ) : null}

      {tab === 'prestamos' ? (
        <Card>
          <CardHeader title="Préstamos" />
          {loansReport.isLoading ? (
            <div className="flex justify-center px-4 py-10">
              <Spinner label="Cargando el reporte" />
            </div>
          ) : null}
          {loansReport.isError ? (
            <div className="px-4 py-4">
              <ErrorState
                message={describeError(loansReport.error).message}
                onRetry={() => void loansReport.refetch()}
              />
            </div>
          ) : null}
          {loansReport.data ? (
            <div className="grid gap-4 px-4 py-4 sm:grid-cols-2 sm:px-5">
              {(
                [
                  ['Como prestatario', loansReport.data.as_borrower],
                  ['Como prestamista', loansReport.data.as_lender],
                ] as const
              ).map(([title, summary]) => (
                <div key={title} className="rounded-lg border border-slate-200 p-4">
                  <p className="text-sm font-semibold text-slate-900">{title}</p>
                  <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <dt className="text-xs text-slate-500">Préstamos activos</dt>
                      <dd className="font-medium text-slate-900">{summary.active_loans}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-slate-500">Pendiente</dt>
                      <dd>
                        <MoneyAmount
                          value={summary.outstanding_amount}
                          currency={currency}
                          className="font-medium text-slate-900"
                        />
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-slate-500">Interés</dt>
                      <dd>
                        <MoneyAmount
                          value={summary.interest_amount}
                          currency={currency}
                          className="font-medium text-slate-900"
                        />
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-slate-500">Próximas cuotas</dt>
                      <dd className="font-medium text-slate-900">
                        {summary.next_installments.length}
                      </dd>
                    </div>
                  </dl>
                </div>
              ))}
            </div>
          ) : null}
        </Card>
      ) : null}

      {tab === 'inversiones' ? (
        <Card>
          <CardHeader title="Inversiones" />
          {investments.isLoading ? (
            <div className="flex justify-center px-4 py-10">
              <Spinner label="Cargando el reporte" />
            </div>
          ) : null}
          {investments.isError ? (
            <div className="px-4 py-4">
              <ErrorState
                message={describeError(investments.error).message}
                onRetry={() => void investments.refetch()}
              />
            </div>
          ) : null}
          {investments.data ? (
            <div className="grid gap-4 px-4 py-4 sm:grid-cols-3 sm:px-5">
              <div>
                <p className="text-xs text-slate-500">Capital invertido</p>
                <MoneyAmount
                  value={investments.data.total_invested}
                  currency={currency}
                  className="text-lg font-semibold text-slate-900"
                />
              </div>
              <div>
                <p className="text-xs text-slate-500">Interés esperado</p>
                <MoneyAmount
                  value={investments.data.interest_expected}
                  currency={currency}
                  className="text-lg font-semibold text-slate-900"
                />
              </div>
              <div>
                <p className="text-xs text-slate-500">Interés ganado</p>
                <MoneyAmount
                  value={investments.data.interest_earned}
                  currency={currency}
                  className="text-lg font-semibold text-slate-900"
                />
              </div>
            </div>
          ) : null}
        </Card>
      ) : null}
    </div>
  )
}
