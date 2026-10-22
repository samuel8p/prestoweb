import { useMemo, useState } from 'react'

import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card, CardHeader } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { Modal } from '../../components/ui/Modal'
import { PageHeader } from '../../components/ui/PageHeader'
import { Select } from '../../components/ui/Select'
import { Input } from '../../components/ui/Input'
import { defaultReportRange } from '../../lib/dates'
import type { Currency } from '../../lib/money/format'
import { useAccounts } from './api'
import { CreateWalletForm } from './CreateWalletForm'
import { MovementForm } from './MovementForm'
import { MovementList } from './MovementList'
import { WalletCard } from './WalletCard'
import { useMovements } from './useMovements'

const CURRENCY_OPTIONS = [
  { value: 'ARS', label: 'Pesos (ARS)' },
  { value: 'USD', label: 'Dólares (USD)' },
]

/** Pantalla de billeteras y movimientos. */
export function WalletsPage() {
  const accounts = useAccounts()
  const [currency, setCurrency] = useState<Currency>('ARS')
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
          <>
            <Button variant="secondary" onClick={() => setWalletOpen(true)}>
              Abrir billetera
            </Button>
            <Button onClick={() => setMovementOpen(true)}>Nuevo movimiento</Button>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <Select
          label="Moneda"
          value={currency}
          options={CURRENCY_OPTIONS}
          onChange={(event) => setCurrency(event.target.value as Currency)}
        />
        <div className="grid grid-cols-2 gap-3">
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
      </div>

      {accounts.isError ? (
        <Alert tone="danger">No pudimos cargar tus billeteras. Probá de nuevo en un momento.</Alert>
      ) : null}

      {account ? (
        <WalletCard account={account} />
      ) : (
        <Card>
          <EmptyState
            title={`Todavía no tenés una billetera en ${currency}`}
            description="Abrí una billetera para poder mover dinero en esa moneda."
            action={
              <Button size="sm" onClick={() => setWalletOpen(true)}>
                Abrir billetera en {currency}
              </Button>
            }
          />
        </Card>
      )}

      <Card>
        <CardHeader
          title="Movimientos"
          description={`En ${currency}, del ${range.from} al ${range.to}.`}
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

      <Modal open={movementOpen} title="Nuevo movimiento" onClose={() => setMovementOpen(false)}>
        <MovementForm defaultCurrency={currency} onDone={() => setMovementOpen(false)} />
      </Modal>

      <Modal open={walletOpen} title="Abrir billetera" onClose={() => setWalletOpen(false)}>
        <CreateWalletForm existingCurrency={currency} onDone={() => setWalletOpen(false)} />
      </Modal>
    </div>
  )
}
