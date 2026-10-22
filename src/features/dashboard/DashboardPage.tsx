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

type QuickAction = 'deposit' | 'withdrawal' | 'transfer'

/** Panel principal: bloque de saldo, movimientos y avisos. */
export function DashboardPage() {
  const accounts = useAccounts()
  const notifications = useNotifications(5)
  const [movementOpen, setMovementOpen] = useState(false)
  const [quickAction, setQuickAction] = useState<QuickAction>('deposit')
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

  function openQuickAction(action: QuickAction) {
    setQuickAction(action)
    setMovementOpen(true)
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Panel" description="Tus saldos, tus movimientos y tus avisos." />

      {/* Bloque de saldo: único gradiente de la app */}
      <section
        aria-labelledby="titulo-saldos"
        className="on-dark relative overflow-hidden rounded-[var(--radius-card)] bg-[linear-gradient(135deg,#06303A_0%,#0B4A57_100%)] shadow-raised animate-fade-up"
      >
        <div aria-hidden="true" className="wave-pattern pointer-events-none absolute inset-0" />

        <div className="relative px-5 py-6 sm:px-8 sm:py-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 id="titulo-saldos" className="label-caps text-white/55">
                Saldo disponible
              </h2>
              <p className="mt-1 text-[13px] text-white/45">
                Por moneda, sin convertirlas entre sí
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                variant="onDark"
                size="sm"
                icon="arrowDownLeft"
                onClick={() => openQuickAction('deposit')}
              >
                Depositar
              </Button>
              <Button
                variant="onDark"
                size="sm"
                icon="arrowUpRight"
                onClick={() => openQuickAction('withdrawal')}
              >
                Retirar
              </Button>
              <Button
                variant="onDark"
                size="sm"
                icon="swap"
                onClick={() => openQuickAction('transfer')}
              >
                Transferir
              </Button>
            </div>
          </div>

          {accounts.isLoading ? (
            <div className="mt-7 grid gap-8 sm:grid-cols-2">
              <div className="h-12 w-40 animate-pulse rounded-lg bg-white/10" />
              <div className="h-12 w-40 animate-pulse rounded-lg bg-white/10" />
            </div>
          ) : null}

          {!accounts.isLoading && wallets.length === 0 ? (
            <div className="mt-6 rounded-[var(--radius-control)] bg-white/5 px-4 py-3">
              <p className="text-[13px] font-semibold text-white/85">Todavía no tenés billeteras</p>
              <p className="mt-0.5 text-[13px] text-white/50">
                Abrí una para empezar a mover dinero.{' '}
                <Link to="/billetera" className="font-semibold text-turquoise underline">
                  Abrir billetera
                </Link>
              </p>
            </div>
          ) : null}

          <div className="mt-7 grid gap-8 sm:grid-cols-2">
            {wallets.map((account) => (
              <div key={account.id}>
                <p className="label-caps text-turquoise">{account.currency}</p>
                <p className="mt-2 text-[40px] font-bold leading-none tracking-tight text-white tabular sm:text-[44px]">
                  <MoneyAmount
                    value={account.balance}
                    currency={account.currency === 'USD' ? 'USD' : 'ARS'}
                    className="[&>span]:text-inherit"
                  />
                </p>
                <p className="mt-2 truncate text-xs text-white/40 tabular">
                  Billetera {account.id.slice(0, 8)}…
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Movimientos: ritmo de tabla */}
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
                  className="text-[13px] font-semibold text-teal hover:underline"
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
              illustration="empty"
              action={
                <Button size="sm" onClick={() => openQuickAction('deposit')}>
                  Depositar
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

        {/* Avisos: ritmo de lista con marca de tiempo */}
        <Card>
          <CardHeader
            title="Avisos"
            icon="bell"
            action={
              <Link to="/avisos" className="text-[13px] font-semibold text-teal hover:underline">
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
              illustration="empty"
            />
          ) : (
            <ul className="px-5 py-2">
              {avisos.map((notification) => (
                <li
                  key={notification.id}
                  className="relative border-l-2 border-line py-3 pl-4 transition-colors hover:border-teal/40"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-semibold text-ink">
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
                  <p className="mt-0.5 text-xs text-ink-subtle tabular">
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
        title={
          quickAction === 'deposit'
            ? 'Depositar'
            : quickAction === 'withdrawal'
              ? 'Retirar'
              : 'Transferir'
        }
        description="El movimiento queda registrado en el libro mayor."
        onClose={() => setMovementOpen(false)}
      >
        <MovementForm
          defaultCurrency={activeCurrency}
          initialType={quickAction}
          onDone={() => setMovementOpen(false)}
        />
      </Modal>
    </div>
  )
}
