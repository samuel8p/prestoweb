import { MoneyAmount } from '../../components/ui/MoneyAmount'
import { percentOf } from '../../lib/money/decimal'
import { formatMoney } from '../../lib/money/format'
import type { Currency } from '../../lib/money/format'
import type { SpendingCategory } from '../../lib/api/types'

export interface SpendingChartProps {
  categories: SpendingCategory[]
  currency: Currency
}

/**
 * Gráfico de barras del gasto por categoría.
 *
 * SVG dibujado a mano (sin librerías): el ancho de cada barra sale del
 * porcentaje calculado sobre los importes del ledger, nunca de un `float`.
 */
export function SpendingChart({ categories, currency }: SpendingChartProps) {
  const [largest, ...rest] = categories
  const max = largest?.amount ?? '0.00'

  return (
    <ul className="space-y-3">
      {[largest, ...rest].map((category, index) => {
        if (!category) {
          return null
        }

        const width = percentOf(category.amount, max)

        return (
          <li key={category.category_id}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="truncate-1 text-[13px] font-medium text-ink">
                {category.category_name}
              </span>
              <span className="shrink-0 text-[13px] font-semibold text-ink tabular">
                <MoneyAmount value={category.amount} currency={currency} />
              </span>
            </div>

            <div
              role="img"
              aria-label={`${category.category_name}: ${formatMoney(category.amount, currency)}`}
              className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-line"
            >
              <div
                className="bar-fill h-full rounded-full bg-primary"
                style={{ width: `${Math.max(width, 2)}%` }}
              />
            </div>

            <p className="mt-1 text-xs text-ink-subtle">
              {category.movements} {category.movements === 1 ? 'movimiento' : 'movimientos'}
              {index === 0 ? ' · la categoría con más gasto' : ''}
            </p>
          </li>
        )
      })}
    </ul>
  )
}
