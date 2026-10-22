import type { ReactNode } from 'react'

import { Icon } from './Icon'
import type { IconName } from './Icon'

export interface StatCardProps {
  /** Etiqueta del indicador (por ejemplo, "Saldo disponible"). */
  label: string
  /** Valor principal. */
  value: ReactNode
  /** Texto de apoyo bajo el valor. */
  hint?: ReactNode
  /** Etiqueta de la moneda, para dejar claro que no se mezclan. */
  currency?: string
  icon?: IconName
  /** Acción secundaria (un link, un botón). */
  action?: ReactNode
}

/**
 * Indicador destacado.
 *
 * Un dato por tarjeta: no resume ni suma importes de monedas distintas.
 */
export function StatCard({ label, value, hint, currency, icon, action }: StatCardProps) {
  return (
    <div className="rounded-[var(--radius-card)] border border-line bg-surface p-5 shadow-card transition-[transform,box-shadow] duration-200 ease-out hover:-translate-y-0.5 hover:shadow-raised">
      <div className="flex items-start justify-between gap-3">
        <p className="label-caps text-ink-subtle">{label}</p>
        {icon ? (
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-tint text-primary">
            <Icon name={icon} size={16} />
          </span>
        ) : null}
      </div>

      <p className="mt-3 text-2xl font-bold tracking-tight text-ink tabular">{value}</p>

      <div className="mt-1.5 flex items-center justify-between gap-3">
        {hint ? <p className="truncate-1 text-xs text-ink-muted">{hint}</p> : <span />}
        {currency ? (
          <span className="shrink-0 rounded bg-surface-muted px-1.5 py-0.5 text-[11px] font-bold text-ink-muted">
            {currency}
          </span>
        ) : null}
      </div>

      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  )
}
