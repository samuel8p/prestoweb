import { formatMoney } from '../../lib/money/format'
import type { Currency } from '../../lib/money/format'

export interface MoneyAmountProps {
  value: string
  currency: Currency
  className?: string
  /** Muestra el importe en positivo (para gastos o movimientos de salida). */
  absolute?: boolean
}

/**
 * Importe de dinero.
 *
 * El string decimal del backend se formatea sin pasar por `Number`: nunca se
 * pierde precisión ni se mezclan monedas.
 */
export function MoneyAmount({
  value,
  currency,
  className = '',
  absolute = false,
}: MoneyAmountProps) {
  const formatted = formatMoney(absolute ? value.replace('-', '') : value, currency)

  return <span className={`tabular ${className}`}>{formatted}</span>
}
