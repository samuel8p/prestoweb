import { Badge } from '../../components/ui/Badge'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import { formatDateTime } from '../../lib/money/format'
import type { MovementReportRow } from '../../lib/api/types'

const TYPE_LABEL: Record<string, string> = {
  deposit: 'Depósito',
  withdrawal: 'Retiro',
  transfer: 'Transferencia',
  interest: 'Interés',
  fee: 'Comisión',
  reversal: 'Reverso',
}

export interface MovementRowProps {
  movement: MovementReportRow
  /** `true` si el movimiento fue revertido por un staff. */
  reversed?: boolean
}

/** Una fila del historial de movimientos. */
export function MovementRow({ movement, reversed = false }: MovementRowProps) {
  const isOutgoing = movement.type === 'withdrawal' || movement.type === 'fee'

  return (
    <li className="flex items-start justify-between gap-3 px-4 py-3 sm:px-5">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-medium text-slate-900">
            {TYPE_LABEL[movement.type] ?? movement.type}
          </p>
          {reversed ? <Badge tone="danger">Revertido</Badge> : null}
          {movement.type === 'reversal' ? (
            <Badge tone="warning">Compensa otro movimiento</Badge>
          ) : null}
        </div>
        {movement.description ? (
          <p className="mt-0.5 truncate text-sm text-slate-500">{movement.description}</p>
        ) : null}
        <p className="mt-0.5 text-xs text-slate-400">{formatDateTime(movement.occurred_at)}</p>
      </div>

      <div className="shrink-0 text-right">
        <MoneyAmount
          value={movement.amount}
          currency={movement.currency === 'USD' ? 'USD' : 'ARS'}
          className={`text-sm font-semibold ${isOutgoing ? 'text-rose-600' : 'text-slate-900'}`}
        />
        <p className="mt-0.5 text-xs text-slate-400">{movement.currency}</p>
      </div>
    </li>
  )
}
