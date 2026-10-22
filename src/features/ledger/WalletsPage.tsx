import { useMemo, useState } from 'react'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card, CardHeader } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { Input } from '../../components/ui/Input'
import { Modal } from '../../components/ui/Modal'
import { PageHeader } from '../../components/ui/PageHeader'
import { Segmented } from '../../components/ui/Segmented'
import { defaultReportRange } from '../../lib/dates'
import { useAccounts } from './api'
import { CreateWalletForm } from './CreateWalletForm'
import { MovementForm } from './MovementForm'
import { MovementList } from './MovementList'
import { WalletCard } from './WalletCard'
import { useMovements } from './useMovements'

const CURRENCY_OPTIONS = [
  { value: 'ARS' as const, label: 'Pesos (ARS)' },
  { value: 'USD' as const, label: 'Dólares (USD)' },
]

/** Pantalla de billeteras y movimientos. */
export function WalletsPage() {
  const accounts = useAccounts()
  const [currency, setCurrency] = useState<'ARS' | 'USD'>('ARS')
  const [range, setRange] = useState(() => defaultReportRange())
  const [movementOpen, setMovementOpen] = useState(false)
  const [walletOpen, setWalletOpen] = useState(false)

  const account = useMemo(
    () => accounts.data?.results.find((item) => item.currency === currency),
    [accounts.data, currency],
  )

  const movements = useMovements({ currency, from: range.from, to: range.to })
  const rows = movements.data?.pages.flatMap((page) => page.results) ?? []

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Billetera y movimientos"
        description="Depositá, retirá y transferí dinero entre billeteras."
        action={
          <Button icon="plus" onClick={() => setMovementOpen(true)}>
            Nuevo movimiento
          </Button>
        }
      />

      {/* Filtros */}
      <Card>
        <div className="flex flex-wrap items-end gap-4 px-5 py-4">
          <div className="flex flex-col gap-1.5">
            <span className="text-[13px] font-medium text-slate-700">Moneda</span>
            <Segmented
              label="Moneda"
              value={currency}
              options={CURRENCY_OPTIONS}
              onChange={setCurrency}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <span className="text-[13px] font-medium text-slate-700">Desde</span>
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
            <span className="text-[13px] font-medium text-slate-700">Hasta</span>
            <Input
              label="Hasta"
              type="date"
              hideLabel
              value={range.to}
              onChange={(event) => setRange((current) => ({ ...current, to: event.target.value }))}
            />
          </div>

          <div className="ml-auto">
            {!account ? (
              <Button variant="secondary" icon="plus" onClick={() => setWalletOpen(true)}>
                Abrir billetera {currency}
              </Button>
            ) : null}
          </div>
        </div>
      </Card>

      {accounts.isError ? (
        <Alert tone="danger">No pudimos cargar tus billeteras. Probá de nuevo en un momento.</Alert>
      ) : null}

      {/* Saldo */}
      {account ? (
        <WalletCard account={account} selected />
      ) : (
        <Card>
          <EmptyState
            title={`Todavía no tenés una billetera en ${currency}`}
            description="Abrí una billetera para poder mover dinero en esa moneda."
            icon="wallet"
            action={
              <Button size="sm" icon="plus" onClick={() => setWalletOpen(true)}>
                Abrir billetera en {currency}
              </Button>
            }
          />
        </Card>
      )}

      {/* Movimientos */}
      <Card>
        <CardHeader
          title="Movimientos"
          description={`En ${currency}, del ${range.from} al ${range.to}.`}
          icon="swap"
        />
        <MovementList
          movements={rows}
          isLoading={movements.isLoading}
          error={movements.error}
          hasNextPage={movements.hasNextPage}
          isFetchingMore={movements.isFetchingNextPage}
          onRetry={() => void movements.refetch()}
          onLoadMore={() => void movements.fetchNextPage()}
        />
      </Card>

      <Modal
        open={movementOpen}
        title="Nuevo movimiento"
        description="Depositá, retirá o transferí dinero."
        onClose={() => setMovementOpen(false)}
      >
        <MovementForm defaultCurrency={currency} onDone={() => setMovementOpen(false)} />
      </Modal>

      <Modal
        open={walletOpen}
        title="Abrir billetera"
        description="Una billetera por moneda."
        onClose={() => setWalletOpen(false)}
      >
        <CreateWalletForm existingCurrency={currency} onDone={() => setWalletOpen(false)} />
      </Modal>
    </div>
  )
}
