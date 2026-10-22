import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card, CardHeader } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { Modal } from '../../components/ui/Modal'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import { PageHeader } from '../../components/ui/PageHeader'
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
import { BalanceCards } from './BalanceCards'
import { QuickActions } from './QuickActions'
import { Shortcuts } from './Shortcuts'
import { nextInstallmentShortcut } from './nextInstallmentShortcut'
import type { Shortcut } from './Shortcuts'

type QuickActionId = 'ingresar' | 'transferir' | 'retirar' | 'billetera'

const MOVEMENT_TYPE: Record<QuickActionId, 'deposit' | 'withdrawal' | 'transfer' | null> = {
  ingresar: 'deposit',
  transferir: 'transfer',
  retirar: 'withdrawal',
  billetera: null,
}

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
  const [movementType, setMovementType] = useState<'deposit' | 'withdrawal' | 'transfer' | null>(
    null,
  )
  const [walletCurrency, setWalletCurrency] = useState<Currency | null>(null)
  const [walletId, setWalletId] = useState<string | null>(null)

  const movements = useMovements({ currency })
  const rows = movements.data?.pages.flatMap((page) => page.results) ?? []

  const wallets = accounts.data?.results ?? []
  const activeAccount = wallets.find((account) => account.currency === currency)

  // Las fichas abren los mismos formularios que usaba Billetera.
  useEffect(() => {
    const unregister = [
      register('ingresar', () => setMovementType('deposit')),
      register('transferir', () => setMovementType('transfer')),
      register('retirar', () => setMovementType('withdrawal')),
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

  function handleQuickAction(id: string) {
    if (id === 'billetera') {
      setWalletId(activeAccount?.id ?? null)
      return
    }

    const type = MOVEMENT_TYPE[id as QuickActionId]
    if (type) {
      setMovementType(type)
      return
    }

    run(id)
  }

  const firstName = user?.first_name?.trim()

  return (
    <div className="flex animate-fade-up flex-col gap-6">
      <PageHeader
        title={firstName ? `Hola, ${firstName}` : 'Hola'}
        description="Tus saldos, tus accesos y lo que viene."
      />

      {accounts.isError ? (
        <Alert tone="danger">No pudimos cargar tus billeteras. Probá de nuevo en un momento.</Alert>
      ) : null}

      {/* Saldos */}
      {accounts.isLoading ? (
        <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
          <div className="h-56 animate-pulse rounded-[1.25rem] bg-chrome/20" />
          <div className="h-40 animate-pulse rounded-[1.25rem] bg-line/60" />
        </div>
      ) : (
        <BalanceCards
          accounts={wallets}
          currency={currency}
          onCurrencyChange={setCurrency}
          onCreateWallet={setWalletCurrency}
        />
      )}

      {/* Acciones rápidas */}
      <QuickActions onAction={handleQuickAction} />

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
        title={
          movementType === 'deposit'
            ? 'Ingresar dinero'
            : movementType === 'withdrawal'
              ? 'Retirar dinero'
              : 'Transferir dinero'
        }
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

      {/* Identificador de la billetera: el backend no expone alias */}
      <Modal
        open={walletId !== null}
        title="Tu billetera"
        description="Compartí este identificador para recibir transferencias."
        onClose={() => setWalletId(null)}
      >
        <div className="flex flex-col gap-4">
          <p className="rounded-[var(--radius-control)] bg-surface-muted p-4 text-center text-sm font-semibold text-ink tabular">
            {walletId}
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setWalletId(null)}>
              Cerrar
            </Button>
            <Button
              icon="wallet"
              onClick={() => {
                if (walletId) {
                  void navigator.clipboard?.writeText(walletId)
                }
              }}
            >
              Copiar identificador
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
