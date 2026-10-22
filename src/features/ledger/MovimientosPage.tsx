import { useState } from 'react'

import { Card, CardHeader } from '../../components/ui/Card'
import { Input } from '../../components/ui/Input'
import { PageHeader } from '../../components/ui/PageHeader'
import { Segmented } from '../../components/ui/Segmented'
import { defaultReportRange } from '../../lib/dates'
import type { Currency } from '../../lib/money/format'
import { MovementList } from './MovementList'
import { useMovements } from './useMovements'

const CURRENCY_OPTIONS = [
  { value: 'ARS' as const, label: 'Pesos (ARS)' },
  { value: 'USD' as const, label: 'Dólares (USD)' },
]

/**
 * Historial de movimientos.
 *
 * La pantalla completa: los saldos y las acciones viven en Inicio; acá está el
 * historial paginado con sus filtros.
 */
export function MovimientosPage() {
  const [currency, setCurrency] = useState<Currency>('ARS')
  const [range, setRange] = useState(() => defaultReportRange())

  const movements = useMovements({ currency, from: range.from, to: range.to })
  const rows = movements.data?.pages.flatMap((page) => page.results) ?? []

  return (
    <div className="flex animate-fade-up flex-col gap-6">
      <PageHeader
        title="Movimientos"
        description="El historial completo de tu billetera, con filtros por moneda y fecha."
      />

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
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Todos los movimientos"
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
          emptyTitle="No hay movimientos en el período"
          emptyDescription="Probá con otras fechas o con la otra moneda."
        />
      </Card>
    </div>
  )
}
