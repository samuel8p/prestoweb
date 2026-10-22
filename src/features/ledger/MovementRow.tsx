import { Badge } from '../../components/ui/Badge'
import { Icon } from '../../components/ui/Icon'
import type { IconName } from '../../components/ui/Icon'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import { formatDateTime } from '../../lib/money/format'
import type { MovementReportRow } from '../../lib/api/types'

type Tone = 'positive' | 'negative' | 'info' | 'neutral'

const TYPE_META: Record<string, { label: string; icon: IconName; tone: Tone }> = {
  deposit: { label: 'Depósito', icon: 'arrowDownLeft', tone: 'positive' },
  withdrawal: { label: 'Retiro', icon: 'arrowUpRight', tone: 'negative' },
  transfer: { label: 'Transferencia', icon: 'swap', tone: 'info' },
  interest: { label: 'Interés', icon: 'trending', tone: 'positive' },
  fee: { label: 'Comisión', icon: 'coins', tone: 'neutral' },
  reversal: { label: 'Reverso', icon: 'refresh', tone: 'neutral' },
}

const TONE_CLASSES: Record<Tone, string> = {
  positive: 'bg-emerald-50 text-emerald-700',
  negative: 'bg-slate-100 text-slate-600',
  info: 'bg-brand-50 text-brand-700',
  neutral: 'bg-slate-100 text-slate-600',
}

export interface MovementRowProps {
  movement: MovementReportRow
  /** `true` si el movimiento fue revertido por un staff. */
  reversed?: boolean
}

/** Una fila del historial de movimientos. */
export function MovementRow({ movement, reversed = false }: MovementRowProps) {
  const meta = TYPE_META[movement.type] ?? {
    label: movement.type,
    icon: 'swap' as IconName,
    tone: 'neutral' as Tone,
  }
  const currency = movement.currency === 'USD' ? 'USD' : 'ARS'

  return (
    <li className="grid grid-cols-[auto_1fr_auto] items-center gap-3 px-5 py-3 sm:gap-4">
      <span
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${TONE_CLASSES[meta.tone]}`}
      >
        <Icon name={meta.icon} size={17} />
      </span>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-medium text-slate-900">{meta.label}</p>
          {reversed ? (
            <Badge tone="danger" dot>
              Revertido
            </Badge>
          ) : null}
          {movement.type === 'reversal' ? (
            <Badge tone="warning" dot>
              Compensa otro movimiento
            </Badge>
          ) : null}
        </div>
        {movement.description ? (
          <p className="mt-0.5 truncate text-[13px] text-slate-500">{movement.description}</p>
        ) : null}
      </div>

      <div className="text-right">
        <MoneyAmount
          value={movement.amount}
          currency={currency}
          className={`text-sm font-semibold ${movement.type === 'withdrawal' ? 'text-slate-900' : 'text-slate-900'}`}
        />
        <p className="mt-0.5 text-[11px] text-slate-400 tabular">
          {formatDateTime(movement.occurred_at)}
        </p>
      </div>
    </li>
  )
}
