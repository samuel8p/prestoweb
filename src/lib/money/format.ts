import { parseDecimal } from './decimal'

export type Currency = 'ARS' | 'USD'

const INTEGER_FORMATTER = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 })
const DATE_FORMATTER = new Intl.DateTimeFormat('es-AR', {
  timeZone: 'UTC',
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
})
const DATE_TIME_FORMATTER = new Intl.DateTimeFormat('es-AR', {
  timeZone: 'UTC',
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

const EMPTY = '—'

function safeParse(value: string) {
  try {
    return parseDecimal(value)
  } catch {
    return null
  }
}

/**
 * Formatea un importe para mostrarlo.
 *
 * El importe se parses como string decimal y se arma a mano: nunca pasa por
 * `Number`, así que no se pierde precisión ni se redondea sin querer.
 *
 * @param value - importe como string decimal (`"1500.50"`).
 * @param currency - moneda del importe.
 * @returns el importe formateado, o `"—"` si el string no es válido.
 */
export function formatMoney(value: string, currency: Currency): string {
  const parsed = safeParse(value)
  if (!parsed) {
    return EMPTY
  }

  const sign = parsed.negative ? '-' : ''
  const grouped = INTEGER_FORMATTER.format(parsed.units)
  return `${currency} ${sign}${grouped},${String(parsed.cents).padStart(2, '0')}`
}

/**
 * Formatea una tasa anual en porcentaje.
 *
 * @param value - tasa como string decimal (`"24.00"`).
 * @returns la tasa con dos decimales y el signo de porcentaje.
 */
export function formatRate(value: string): string {
  const parsed = safeParse(value)
  if (!parsed) {
    return EMPTY
  }

  const sign = parsed.negative ? '-' : ''
  const grouped = INTEGER_FORMATTER.format(parsed.units)
  return `${sign}${grouped},${String(parsed.cents).padStart(2, '0')}%`
}

/**
 * Formatea un porcentaje entero.
 *
 * @param value - porcentaje ya calculado.
 * @returns el porcentaje con el signo de porcentaje.
 */
export function formatPercent(value: number): string {
  return `${INTEGER_FORMATTER.format(value)}%`
}

/**
 * Formatea una fecha ISO (`YYYY-MM-DD`) en formato local rioplatense.
 *
 * @param value - fecha como string ISO.
 * @returns la fecha formateada, o `"—"` si no se puede leer.
 */
export function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return EMPTY
  }
  return DATE_FORMATTER.format(date)
}

/**
 * Formatea una fecha y hora ISO en UTC.
 *
 * @param value - fecha y hora como string ISO.
 * @returns la fecha y hora formateadas, o `"—"` si no se puede leer.
 */
export function formatDateTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return EMPTY
  }
  return `${DATE_TIME_FORMATTER.format(date)} UTC`
}

/**
 * Convierte un importe a string decimal sin signo.
 *
 * @param value - importe como string decimal.
 * @returns el importe sin el signo negativo.
 */
export function absoluteDecimal(value: string): string {
  const parsed = safeParse(value)
  if (!parsed) {
    return value
  }
  return `${parsed.units}.${String(parsed.cents).padStart(2, '0')}`
}
