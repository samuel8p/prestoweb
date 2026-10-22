import { Badge } from '../../components/ui/Badge'
import { Icon } from '../../components/ui/Icon'
import type { IconName } from '../../components/ui/Icon'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import { formatDateTime } from '../../lib/money/format'
import type { MovementReportRow } from '../../lib/api/types'

type Flow = 'in' | 'out' | 'neutral'

const TYPE_META: Record<
  string,
  { label: string; icon: IconName; flow: Flow; description: string }
> = {
  deposit: {
    label: 'Depósito',
    icon: 'arrowDownLeft',
    flow: 'in',
    description: 'Entró a tu billetera',
  },
  interest: { label: 'Interés', icon: 'trending', flow: 'in', description: 'Interés acreditado' },
  withdrawal: {
    label: 'Retiro',
    icon: 'arrowUpRight',
    flow: 'out',
    description: 'Salió de tu billetera',
  },
  fee: { label: 'Comisión', icon: 'coins', flow: 'out', description: 'Comisión cobrada' },
  transfer: {
    label: 'Transferencia',
    icon: 'swap',
    flow: 'neutral',
    description: 'Movimiento entre billeteras',
  },
  reversal: {
    label: 'Reverso',
    icon: 'refresh',
    flow: 'neutral',
    description: 'Compensa otro movimiento',
  },
}

const ICON_TONES: Record<Flow, string> = {
  in: 'bg-success-bg text-success',
  out: 'bg-danger-bg text-danger',
  neutral: 'bg-surface-muted text-ink-muted',
}

const AMOUNT_TONES: Record<Flow, string> = {
  in: 'text-success',
  out: 'text-danger',
  neutral: 'text-ink',
}

export interface MovementRowProps {
  movement: MovementReportRow
  /** `true` si el movimiento fue revertido por un staff. */
  reversed?: boolean
  /** Retardo de la entrada escalonada de la lista. */
  index?: number
}

/** Una fila del historial de movimientos. */
export function MovementRow({ movement, reversed = false, index = 0 }: MovementRowProps) {
  const meta = TYPE_META[movement.type] ?? {
    label: movement.type,
    icon: 'swap' as IconName,
    flow: 'neutral' as Flow,
    description: '',
  }
  const currency = movement.currency === 'USD' ? 'USD' : 'ARS'
  const sign = meta.flow === 'in' ? '+' : meta.flow === 'out' ? '−' : ''

  return (
    <li
      className="grid animate-fade-up grid-cols-[auto_1fr_auto] items-center gap-3 px-5 py-3 transition-colors hover:bg-surface-muted sm:gap-4"
      style={{ animationDelay: `${Math.min(index, 8) * 40}ms` }}
    >
      <span
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${ICON_TONES[meta.flow]}`}
      >
        <Icon name={meta.icon} size={17} />
      </span>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold text-ink">{meta.label}</p>
          {reversed ? (
            <Badge tone="danger" dot>
              Revertido
            </Badge>
          ) : null}
        </div>
        <p className="mt-0.5 truncate text-[13px] text-ink-muted">
          {movement.description || meta.description}
        </p>
      </div>

      <div className="text-right">
        <p
          className={`flex items-center justify-end gap-1 text-sm font-bold tabular ${AMOUNT_TONES[meta.flow]}`}
        >
          {sign ? (
            <>
              <span aria-hidden="true">{sign}</span>
              <span className="sr-only">{meta.flow === 'in' ? 'Ingreso de' : 'Egreso de'}</span>
            </>
          ) : null}
          <MoneyAmount value={movement.amount} currency={currency} />
        </p>
        <p className="mt-0.5 text-[11px] text-ink-subtle tabular">
          {formatDateTime(movement.occurred_at)}
        </p>
      </div>
    </li>
  )
}
