import { formatPercent } from '../../lib/money/format'

export interface ProgressBarProps {
  /** Porcentaje ya calculado (0 a 100 o más). */
  percent: number
  label: string
  tone?: 'ok' | 'warning' | 'danger'
}

const TONES = {
  ok: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger: 'bg-rose-500',
} as const

/** Barra de progreso con su porcentaje en texto (accesible sin color). */
export function ProgressBar({ percent, label, tone = 'ok' }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, percent))

  return (
    <div>
      <div
        role="progressbar"
        aria-label={label}
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2 w-full overflow-hidden rounded-full bg-slate-200"
      >
        <div className={`h-full rounded-full ${TONES[tone]}`} style={{ width: `${clamped}%` }} />
      </div>
      <p className="mt-1 text-xs text-slate-500">{formatPercent(percent)}</p>
    </div>
  )
}
