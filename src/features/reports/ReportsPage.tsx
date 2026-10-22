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
import { Segmented } from '../../components/ui/Segmented'
import { SkeletonRows } from '../../components/ui/Skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/Table'
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
import { SpendingChart } from './SpendingChart'

type ReportTab = 'movimientos' | 'gasto' | 'prestamos' | 'inversiones'

const TABS: Array<{ id: ReportTab; label: string }> = [
  { id: 'movimientos', label: 'Movimientos' },
  { id: 'gasto', label: 'Gasto por categoría' },
  { id: 'prestamos', label: 'Préstamos' },
  { id: 'inversiones', label: 'Inversiones' },
]

const CURRENCY_OPTIONS = [
  { value: 'ARS' as const, label: 'Pesos (ARS)' },
  { value: 'USD' as const, label: 'Dólares (USD)' },
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

  const reportKey =
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
    <div className="flex animate-fade-up flex-col gap-6">
      <PageHeader
        title="Reportes"
        description="Resúmenes de tu actividad, en una moneda y un rango de fechas."
        action={
          <Button
            variant="secondary"
            icon="download"
            loading={downloadCsv.isPending}
            onClick={() => void handleDownload()}
          >
            Descargar CSV
          </Button>
        }
      />

      {/* Filtros */}
      <Card>
        <div className="flex flex-wrap items-end gap-5 px-5 py-4">
          <div className="flex flex-col gap-1.5">
            <span className="text-[13px] font-medium text-ink">Moneda</span>
            <Segmented
              label="Moneda"
              value={currency}
              options={CURRENCY_OPTIONS}
              onChange={setCurrency}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <span className="text-[13px] font-medium text-ink">Desde</span>
            <Input
              label="Desde"
              type="date"
              hideLabel
              value={range.from}
              onChange={(event) =>
                setRange((current) => ({ ...current, from: event.target.value }))
              }
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <span className="text-[13px] font-medium text-ink">Hasta</span>
            <Input
              label="Hasta"
              type="date"
              hideLabel
              value={range.to}
              onChange={(event) => setRange((current) => ({ ...current, to: event.target.value }))}
            />
          </div>

          <p className="ml-auto text-xs text-ink-muted">
            El rango máximo es de 12 meses. Los reportes de préstamos e inversiones son del período
            actual.
          </p>
        </div>
      </Card>

      {actionError ? <Alert tone="danger">{actionError}</Alert> : null}

      {/* Pestañas */}
      <div
        role="tablist"
        aria-label="Reportes"
        className="flex flex-wrap gap-1 border-b border-line"
      >
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            onClick={() => setTab(item.id)}
            className={`-mb-px border-b-2 px-3 py-2 text-[13px] font-medium transition-colors ${
              tab === item.id
                ? 'border-teal text-teal'
                : 'border-transparent text-ink-muted hover:text-ink'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Movimientos */}
      {tab === 'movimientos' ? (
        <Card>
          <CardHeader title="Movimientos del período" icon="swap" />
          {movements.isLoading ? <SkeletonRows rows={5} columns={4} /> : null}
          {movements.isError ? (
            <div className="px-5 py-4">
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

          {(movements.data?.results.length ?? 0) > 0 ? (
            <Table>
              <TableHead>
                <TableHeader>Tipo</TableHeader>
                <TableHeader>Descripción</TableHeader>
                <TableHeader>Fecha</TableHeader>
                <TableHeader align="right">Importe</TableHeader>
              </TableHead>
              <TableBody>
                {(movements.data?.results ?? []).map((movement) => (
                  <TableRow key={movement.id}>
                    <TableCell className="font-medium text-ink">{movement.type}</TableCell>
                    <TableCell className="max-w-xs truncate">
                      {movement.description || '—'}
                    </TableCell>
                    <TableCell className="tabular">{formatDate(movement.occurred_at)}</TableCell>
                    <TableCell align="right">
                      <div className="flex items-center justify-end gap-2">
                        <MoneyAmount
                          value={movement.amount}
                          currency={movement.currency === 'USD' ? 'USD' : 'ARS'}
                          className="font-semibold text-ink"
                        />
                        {movement.is_reversed ? (
                          <Badge tone="danger" dot>
                            Revertido
                          </Badge>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : null}
        </Card>
      ) : null}

      {/* Gasto por categoría */}
      {tab === 'gasto' ? (
        <Card>
          <CardHeader
            title="Gasto por categoría"
            description={`Del ${range.from} al ${range.to}.`}
            icon="budget"
          />
          {spending.isLoading ? <SkeletonRows rows={3} columns={2} /> : null}
          {spending.isError ? (
            <div className="px-5 py-4">
              <ErrorState
                message={describeError(spending.error).message}
                onRetry={() => void spending.refetch()}
              />
            </div>
          ) : null}
          {!spending.isLoading &&
          !spending.isError &&
          (spending.data?.categories.length ?? 0) === 0 ? (
            <EmptyState title="No hay gastos categorizados en el período" />
          ) : null}

          {spending.data ? (
            <div className="px-5 py-4">
              <SpendingChart categories={spending.data.categories} currency={currency} />
            </div>
          ) : null}

          {spending.data ? (
            <div className="flex items-center justify-between border-t border-line px-5 py-3.5">
              <p className="text-[13px] font-semibold text-ink">Total del período</p>
              <MoneyAmount
                value={spending.data.total}
                currency={currency}
                className="text-base font-bold text-ink"
              />
            </div>
          ) : null}
        </Card>
      ) : null}

      {/* Préstamos */}
      {tab === 'prestamos' ? (
        <Card>
          <CardHeader title="Préstamos" icon="loan" />
          {loansReport.isLoading ? <SkeletonRows rows={2} columns={4} /> : null}
          {loansReport.isError ? (
            <div className="px-5 py-4">
              <ErrorState
                message={describeError(loansReport.error).message}
                onRetry={() => void loansReport.refetch()}
              />
            </div>
          ) : null}

          {loansReport.data ? (
            <div className="grid gap-px bg-line sm:grid-cols-2">
              {(
                [
                  ['Como prestatario', loansReport.data.as_borrower],
                  ['Como prestamista', loansReport.data.as_lender],
                ] as const
              ).map(([title, summary]) => (
                <dl key={title} className="grid grid-cols-2 gap-5 bg-surface p-5">
                  <div className="col-span-2">
                    <dt className="text-[13px] font-semibold text-ink">{title}</dt>
                  </div>
                  <div>
                    <dt className="label-caps text-ink-subtle">Préstamos activos</dt>
                    <dd className="mt-0.5 text-lg font-semibold text-ink tabular">
                      {summary.active_loans}
                    </dd>
                  </div>
                  <div>
                    <dt className="label-caps text-ink-subtle">Próximas cuotas</dt>
                    <dd className="mt-0.5 text-lg font-semibold text-ink tabular">
                      {summary.next_installments.length}
                    </dd>
                  </div>
                  <div>
                    <dt className="label-caps text-ink-subtle">Pendiente</dt>
                    <dd className="mt-0.5 text-sm font-semibold text-ink tabular">
                      <MoneyAmount value={summary.outstanding_amount} currency={currency} />
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-ink-muted">Interés</dt>
                    <dd className="mt-0.5 text-sm font-semibold text-ink tabular">
                      <MoneyAmount value={summary.interest_amount} currency={currency} />
                    </dd>
                  </div>
                </dl>
              ))}
            </div>
          ) : null}
        </Card>
      ) : null}

      {/* Inversiones */}
      {tab === 'inversiones' ? (
        <Card>
          <CardHeader title="Inversiones" icon="trending" />
          {investments.isLoading ? <SkeletonRows rows={1} columns={3} /> : null}
          {investments.isError ? (
            <div className="px-5 py-4">
              <ErrorState
                message={describeError(investments.error).message}
                onRetry={() => void investments.refetch()}
              />
            </div>
          ) : null}

          {investments.data ? (
            <dl className="grid gap-px bg-line sm:grid-cols-3">
              <div className="bg-surface p-5">
                <dt className="label-caps text-ink-subtle">Capital invertido</dt>
                <dd className="mt-1 text-xl font-semibold text-ink tabular">
                  <MoneyAmount value={investments.data.total_invested} currency={currency} />
                </dd>
              </div>
              <div className="bg-surface p-5">
                <dt className="label-caps text-ink-subtle">Interés esperado</dt>
                <dd className="mt-1 text-xl font-semibold text-ink tabular">
                  <MoneyAmount value={investments.data.interest_expected} currency={currency} />
                </dd>
              </div>
              <div className="bg-surface p-5">
                <dt className="label-caps text-ink-subtle">Interés ganado</dt>
                <dd className="mt-1 text-xl font-semibold text-ink tabular">
                  <MoneyAmount value={investments.data.interest_earned} currency={currency} />
                </dd>
              </div>
            </dl>
          ) : null}
        </Card>
      ) : null}
    </div>
  )
}
