import { MoneyAmount } from '../../components/ui/MoneyAmount'
import { formatDate } from '../../lib/money/format'
import type { Currency } from '../../lib/money/format'
import type { Shortcut } from './Shortcuts'

/**
 * Atajo de la próxima cuota, con los datos del reporte de préstamos.
 *
 * @param currency - la moneda del resumen.
 * @param next - la próxima cuota a pagar, si hay.
 */
export function nextInstallmentShortcut(
  currency: Currency,
  next: { number: number; amount: string; due_date: string } | undefined,
): Shortcut | null {
  if (!next) {
    return null
  }

  return {
    id: 'proxima-cuota',
    label: 'Próxima cuota',
    value: <MoneyAmount value={next.amount} currency={currency} />,
    detail: `Cuota ${next.number} · vence el ${formatDate(next.due_date)}`,
    to: '/prestamos?vista=prestamos',
    icon: 'clock',
  }
}
