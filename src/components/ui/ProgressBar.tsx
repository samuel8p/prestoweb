type Tone = 'ok' | 'warning' | 'danger'

const TONES: Record<Tone, string> = {
  ok: 'bg-brand-600',
  warning: 'bg-amber-500',
  danger: 'bg-rose-500',
}

export interface ProgressBarProps {
  /** Porcentaje ya calculado (0 a 100 o más). */
  percent: number
  label: string
  tone?: Tone
  /** Muestra el porcentaje a la derecha de la barra. */
  showValue?: boolean
}

/** Barra de progreso: fina, con el porcentaje siempre visible. */
export function ProgressBar({ percent, label, tone = 'ok', showValue = true }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, percent))

  return (
    <div>
      <div
        role="progressbar"
        aria-label={label}
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200"
      >
        <div className={`h-full rounded-full ${TONES[tone]}`} style={{ width: `${clamped}%` }} />
      </div>
      {showValue ? (
        <p className="mt-1.5 text-xs font-medium text-slate-500 tabular">{percent}%</p>
      ) : null}
    </div>
  )
}
