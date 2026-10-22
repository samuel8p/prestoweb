import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card, CardHeader } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { Modal } from '../../components/ui/Modal'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import { PageHeader } from '../../components/ui/PageHeader'
import { Segmented } from '../../components/ui/Segmented'
import { StatCard } from '../../components/ui/StatCard'
import { SkeletonRows } from '../../components/ui/Skeleton'
import { formatDateTime } from '../../lib/money/format'
import type { Currency } from '../../lib/money/format'
import { useNotifications } from '../notifications/api'
import { useAccounts } from '../ledger/api'
import { MovementForm } from '../ledger/MovementForm'
import { MovementList } from '../ledger/MovementList'
import { useRecentMovements } from '../ledger/useRecentMovements'

const EVENT_LABEL: Record<string, string> = {
  installment_due_soon: 'Cuota por vencer',
  installment_overdue: 'Cuota vencida',
  investment_settled: 'Inversión liquidada',
  budget_alert: 'Alerta de presupuesto',
}

const CURRENCY_OPTIONS = [
  { value: 'ARS' as const, label: 'ARS' },
  { value: 'USD' as const, label: 'USD' },
]

/** Panel principal: saldos, últimos movimientos y avisos. */
export function DashboardPage() {
  const accounts = useAccounts()
  const notifications = useNotifications(5)
  const [movementOpen, setMovementOpen] = useState(false)
  const [currency, setCurrency] = useState<Currency>('ARS')

  const wallets = accounts.data?.results ?? []
  const availableCurrencies = useMemo(
    () =>
      (accounts.data?.results ?? []).map(
        (account) => (account.currency === 'USD' ? 'USD' : 'ARS') as Currency,
      ),
    [accounts.data],
  )

  const recent = useRecentMovements(availableCurrencies)
  const avisos = notifications.data?.results ?? []

  const activeCurrency = availableCurrencies.includes(currency)
    ? currency
    : (availableCurrencies[0] ?? 'ARS')
  const movements = recent.movements.filter((movement) => movement.currency === activeCurrency)

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Panel"
        description="Tus saldos, tus movimientos y tus avisos."
        action={
          <Button icon="plus" onClick={() => setMovementOpen(true)}>
            Nuevo movimiento
          </Button>
        }
      />

      {/* Saldos por moneda: un dato por billetera, sin sumar monedas */}
      <section aria-labelledby="titulo-billeteras" className="flex flex-col gap-3">
        <h2
          id="titulo-billeteras"
          className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400"
        >
          Saldos
        </h2>

        {accounts.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <StatCard label="Saldo disponible" value="—" />
            <StatCard label="Saldo disponible" value="—" />
          </div>
        ) : null}

        {accounts.isError ? (
          <Card>
            <EmptyState
              title="No pudimos cargar tus billeteras"
              description="Revisá tu conexión y probá de nuevo."
              icon="wallet"
              action={
                <Button
                  size="sm"
                  variant="secondary"
                  icon="refresh"
                  onClick={() => void accounts.refetch()}
                >
                  Reintentar
                </Button>
              }
            />
          </Card>
        ) : null}

        {!accounts.isLoading && !accounts.isError && wallets.length === 0 ? (
          <Card>
            <EmptyState
              title="Todavía no tenés billeteras"
              description="Abrí una billetera para empezar a mover dinero."
              icon="wallet"
              action={
                <Link to="/billetera">
                  <Button size="sm">Abrir billetera</Button>
                </Link>
              }
            />
          </Card>
        ) : null}

        <div className="grid gap-4 sm:grid-cols-2">
          {wallets.map((account) => (
            <StatCard
              key={account.id}
              label={`Saldo ${account.currency}`}
              value={
                <MoneyAmount
                  value={account.balance}
                  currency={account.currency === 'USD' ? 'USD' : 'ARS'}
                />
              }
              icon="wallet"
              hint={`Billetera ${account.id.slice(0, 8)}…`}
            />
          ))}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Movimientos */}
        <Card className="lg:col-span-2">
          <CardHeader
            title="Últimos movimientos"
            icon="swap"
            action={
              <div className="flex items-center gap-3">
                <Segmented
                  label="Moneda de los movimientos"
                  value={activeCurrency}
                  options={CURRENCY_OPTIONS}
                  onChange={setCurrency}
                />
                <Link
                  to="/billetera"
                  className="text-[13px] font-medium text-brand-700 hover:underline"
                >
                  Ver todos
                </Link>
              </div>
            }
          />

          {recent.isLoading ? (
            <SkeletonRows rows={4} columns={3} />
          ) : movements.length === 0 ? (
            <EmptyState
              title="Todavía no hay movimientos"
              description="Empezá con un depósito."
              icon="swap"
              action={
                <Button size="sm" onClick={() => setMovementOpen(true)}>
                  Nuevo movimiento
                </Button>
              }
            />
          ) : (
            <MovementList
              movements={movements}
              isLoading={false}
              error={null}
              hasNextPage={false}
              isFetchingMore={false}
              onRetry={() => void recent.refetch()}
              onLoadMore={() => undefined}
              emptyTitle="Todavía no hay movimientos"
            />
          )}
        </Card>

        {/* Avisos */}
        <Card>
          <CardHeader
            title="Avisos"
            icon="bell"
            action={
              <Link to="/avisos" className="text-[13px] font-medium text-brand-700 hover:underline">
                Ver todos
              </Link>
            }
          />

          {notifications.isLoading ? (
            <SkeletonRows rows={3} columns={2} />
          ) : avisos.length === 0 ? (
            <EmptyState
              title="No tenés avisos"
              description="Acá vas a ver las novedades de tu cuenta."
              icon="bell"
            />
          ) : (
            <ul className="divide-y divide-line">
              {avisos.map((notification) => (
                <li key={notification.id} className="px-5 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-medium text-slate-900">
                      {EVENT_LABEL[notification.event_type] ?? notification.event_type}
                    </p>
                    <Badge
                      tone={
                        notification.status === 'failed'
                          ? 'danger'
                          : notification.status === 'sent'
                            ? 'success'
                            : 'warning'
                      }
                      dot
                    >
                      {notification.status === 'sent'
                        ? 'Enviado'
                        : notification.status === 'failed'
                          ? 'Fallido'
                          : 'Pendiente'}
                    </Badge>
                  </div>
                  <p className="mt-0.5 text-xs text-slate-400 tabular">
                    {formatDateTime(notification.created_at)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Modal
        open={movementOpen}
        title="Nuevo movimiento"
        description="Depositá, retirá o transferí dinero."
        onClose={() => setMovementOpen(false)}
      >
        <MovementForm defaultCurrency={activeCurrency} onDone={() => setMovementOpen(false)} />
      </Modal>
    </div>
  )
}
