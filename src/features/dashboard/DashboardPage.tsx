import { Link } from 'react-router-dom'

import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card, CardHeader } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { PageHeader } from '../../components/ui/PageHeader'
import { Spinner } from '../../components/ui/Spinner'
import { formatDateTime } from '../../lib/money/format'
import type { Currency } from '../../lib/money/format'
import { useNotifications } from '../notifications/api'
import { useAccounts } from '../ledger/api'
import { MovementRow } from '../ledger/MovementRow'
import { WalletCard } from '../ledger/WalletCard'
import { useRecentMovements } from '../ledger/useRecentMovements'

const EVENT_LABEL: Record<string, string> = {
  installment_due_soon: 'Cuota por vencer',
  installment_overdue: 'Cuota vencida',
  investment_settled: 'Inversión liquidada',
  budget_alert: 'Alerta de presupuesto',
}

/** Panel principal: saldos, últimos movimientos y avisos. */
export function DashboardPage() {
  const accounts = useAccounts()
  const notifications = useNotifications(5)

  const currencies = (accounts.data?.results ?? []).map(
    (account) => (account.currency === 'USD' ? 'USD' : 'ARS') as Currency,
  )
  const recent = useRecentMovements(currencies)

  const wallets = accounts.data?.results ?? []
  const avisos = notifications.data?.results ?? []

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Panel"
        description="Tus saldos, tus movimientos y tus avisos."
        action={
          <Link to="/billetera">
            <Button variant="secondary">Ir a la billetera</Button>
          </Link>
        }
      />

      <section aria-labelledby="titulo-billeteras" className="flex flex-col gap-3">
        <h2
          id="titulo-billeteras"
          className="text-sm font-semibold uppercase tracking-wide text-slate-500"
        >
          Billeteras
        </h2>

        {accounts.isLoading ? (
          <div className="flex justify-center py-6">
            <Spinner label="Cargando tus billeteras" />
          </div>
        ) : null}

        {accounts.isError ? (
          <Card>
            <EmptyState
              title="No pudimos cargar tus billeteras"
              description="Revisá tu conexión y probá de nuevo."
              action={
                <Button size="sm" variant="secondary" onClick={() => void accounts.refetch()}>
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
            <WalletCard key={account.id} account={account} />
          ))}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Últimos movimientos"
            action={
              <Link to="/billetera" className="text-sm font-medium text-brand-700 hover:underline">
                Ver todos
              </Link>
            }
          />
          {recent.isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner label="Cargando los movimientos" />
            </div>
          ) : recent.movements.length === 0 ? (
            <EmptyState title="Todavía no hay movimientos" description="Empezá con un depósito." />
          ) : (
            <ul className="divide-y divide-slate-100">
              {recent.movements.map((movement) => (
                <MovementRow
                  key={movement.id}
                  movement={movement}
                  reversed={movement.is_reversed}
                />
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <CardHeader
            title="Avisos"
            action={
              <Link to="/avisos" className="text-sm font-medium text-brand-700 hover:underline">
                Ver todos
              </Link>
            }
          />
          {notifications.isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner label="Cargando los avisos" />
            </div>
          ) : avisos.length === 0 ? (
            <EmptyState title="No tenés avisos" description="Acá vas a ver las novedades." />
          ) : (
            <ul className="divide-y divide-slate-100">
              {avisos.map((notification) => (
                <li
                  key={notification.id}
                  className="flex items-start justify-between gap-3 px-4 py-3 sm:px-5"
                >
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      {EVENT_LABEL[notification.event_type] ?? notification.event_type}
                    </p>
                    <p className="mt-0.5 text-xs text-slate-400">
                      {formatDateTime(notification.created_at)}
                    </p>
                  </div>
                  <Badge tone={notification.status === 'failed' ? 'danger' : 'neutral'}>
                    {notification.status === 'sent'
                      ? 'Enviado'
                      : notification.status === 'failed'
                        ? 'Fallido'
                        : 'Pendiente'}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}
