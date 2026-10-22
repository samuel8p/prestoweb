import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { Card, CardHeader } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { Modal } from '../../components/ui/Modal'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import { SkeletonRows } from '../../components/ui/Skeleton'
import { useActions } from '../../app/action-context'
import type { Currency } from '../../lib/money/format'
import { useAuth } from '../auth/auth-context'
import { useBudgets } from '../budgets/api'
import { useInvestmentsReport, useLoansReport } from '../reports/api'
import { useAccounts } from '../ledger/api'
import { CreateWalletForm } from '../ledger/CreateWalletForm'
import { MovementForm } from '../ledger/MovementForm'
import { MovementList } from '../ledger/MovementList'
import { useMovements } from '../ledger/useMovements'
import { NotificationsPanel } from '../../components/layout/NotificationsPanel'
import { BalanceSurface } from './BalanceSurface'
import { Shortcuts } from './Shortcuts'
import { nextInstallmentShortcut } from './nextInstallmentShortcut'
import type { Shortcut } from './Shortcuts'
import { WalletPanel } from './WalletPanel'

/**
 * Inicio: saldos, accesos rápidos, movimientos recientes y accesos compactos.
 *
 * Absorbe la pantalla de Billetera: los saldos por moneda y las fichas de
 * acción viven acá; el historial completo queda en su propia ruta.
 */
export function InicioPage() {
  const { register, run } = useActions()
  const { user } = useAuth()
  const accounts = useAccounts()
  const budgets = useBudgets()
  const loansReport = useLoansReport('ARS')
  const investments = useInvestmentsReport('ARS')

  const [currency, setCurrency] = useState<Currency>('ARS')
  const [movementType, setMovementType] = useState<'deposit' | 'transfer' | null>(null)
  const [walletCurrency, setWalletCurrency] = useState<Currency | null>(null)
  const [walletOpen, setWalletOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)

  const movements = useMovements({ currency })
  const rows = movements.data?.pages.flatMap((page) => page.results) ?? []

  const wallets = accounts.data?.results ?? []

  // Las fichas abren los mismos formularios que usaba Billetera.
  useEffect(() => {
    const unregister = [
      register('ingresar', () => setMovementType('deposit')),
      register('transferir', () => setMovementType('transfer')),
    ]
    return () => unregister.forEach((off) => off())
  }, [register])

  const shortcuts = useMemo<Shortcut[]>(() => {
    const list: Shortcut[] = []

    const next = loansReport.data?.as_borrower.next_installments[0]
    const installment = nextInstallmentShortcut(currency, next)
    if (installment) {
      list.push(installment)
    }

    const position = investments.data?.positions[0]
    if (position) {
      list.push({
        id: 'inversion',
        label: 'Inversión activa',
        value: <MoneyAmount value={position.amount} currency={currency} />,
        detail: `Interés ${position.interest_amount} · vence el ${position.maturity_date}`,
        to: '/inversiones',
        icon: 'trending',
      })
    }

    const budget = budgets.data?.results?.[0]
    if (budget) {
      list.push({
        id: 'presupuesto',
        label: `Presupuesto · ${budget.category.name}`,
        value: <MoneyAmount value={budget.limit_amount} currency={budget.currency} />,
        detail: `Límite mensual en ${budget.currency}`,
        to: '/presupuestos',
        icon: 'budget',
      })
    }

    return list
  }, [budgets.data, currency, investments.data, loansReport.data])

  const firstName = user?.first_name?.trim()

  return (
    <div className="flex animate-fade-up flex-col gap-6">
      {/* Superficie en L: saludo, pestañas, lupa, campana, saldo y acciones */}
      {accounts.isLoading ? (
        <div className="h-72 animate-pulse rounded-[24px] bg-line/60" />
      ) : (
        <BalanceSurface
          accounts={wallets}
          currency={currency}
          onCurrencyChange={setCurrency}
          greeting={firstName ? `Hola, ${firstName}` : 'Hola'}
          onSearch={() => run('buscar')}
          onNotifications={() => setNotificationsOpen((open) => !open)}
          notificationsPanel={
            <NotificationsPanel
              open={notificationsOpen}
              onClose={() => setNotificationsOpen(false)}
            />
          }
          onDeposit={() => setMovementType('deposit')}
          onTransfer={() => setMovementType('transfer')}
          onWallet={() => setWalletOpen(true)}
          onCreateWallet={setWalletCurrency}
        />
      )}

      {/* Movimientos y accesos */}
      <div className="grid gap-6 lg:grid-cols-[1.7fr_1fr]">
        <Card>
          <CardHeader
            title="Movimientos recientes"
            icon="swap"
            action={
              <Link
                to="/billetera"
                className="text-[13px] font-semibold text-primary hover:underline"
              >
                Ver todos
              </Link>
            }
          />

          {movements.isLoading ? (
            <SkeletonRows rows={4} columns={3} />
          ) : (
            <MovementList
              movements={rows.slice(0, 5)}
              isLoading={false}
              error={movements.error}
              hasNextPage={false}
              isFetchingMore={false}
              onRetry={() => void movements.refetch()}
              onLoadMore={() => undefined}
              emptyTitle="Todavía no hay movimientos"
              emptyDescription="Usá las fichas de arriba para ingresar dinero."
            />
          )}
        </Card>

        <Card>
          <CardHeader title="Accesos" icon="sliders" />
          <div className="px-4 py-4">
            {shortcuts.length === 0 ? (
              <EmptyState
                title="Nada pendiente por ahora"
                description="Acá vas a ver tu próxima cuota, tus inversiones y tus presupuestos."
                illustration="empty"
              />
            ) : (
              <Shortcuts shortcuts={shortcuts} />
            )}
          </div>
        </Card>
      </div>

      {/* Modales */}
      <Modal
        open={movementType !== null}
        title={movementType === 'deposit' ? 'Ingresar dinero' : 'Transferir dinero'}
        description="El movimiento queda registrado en el libro mayor."
        onClose={() => setMovementType(null)}
      >
        {movementType ? (
          <MovementForm
            defaultCurrency={currency}
            initialType={movementType}
            onDone={() => setMovementType(null)}
          />
        ) : null}
      </Modal>

      <Modal
        open={walletOpen}
        title="Tu billetera"
        description="Tu alias y los identificadores de tus cuentas."
        onClose={() => setWalletOpen(false)}
      >
        <WalletPanel accounts={wallets} onDone={() => setWalletOpen(false)} />
      </Modal>

      <Modal
        open={walletCurrency !== null}
        title="Abrir billetera"
        description="Una billetera por moneda."
        onClose={() => setWalletCurrency(null)}
      >
        {walletCurrency ? (
          <CreateWalletForm
            existingCurrency={walletCurrency}
            onDone={() => setWalletCurrency(null)}
          />
        ) : null}
      </Modal>
    </div>
  )
}
