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
    <div className="rounded-[var(--radius-card)] border border-line bg-surface p-5 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[13px] font-medium text-slate-500">{label}</p>
        {icon ? (
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
            <Icon name={icon} size={17} />
          </span>
        ) : null}
      </div>

      <p className="mt-3 text-2xl font-semibold tracking-tight text-slate-900 tabular">{value}</p>

      <div className="mt-1.5 flex items-center justify-between gap-3">
        {hint ? <p className="truncate-1 text-xs text-slate-500">{hint}</p> : <span />}
        {currency ? (
          <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-semibold text-slate-600">
            {currency}
          </span>
        ) : null}
      </div>

      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  )
}
