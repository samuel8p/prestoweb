/**
 * Aritmética de importes sobre strings decimales.
 *
 * Los importes de la API llegan como string decimal (`"1500.50"`). Nunca se
 * convierten a `Number`: un `float` no puede representar exacto cualquier
 * importe con dos decimales y compararlos perdería precisión. Acá se parses
 * el string a un entero escalado (importe x 100) con `BigInt`, que es exacto.
 */

const DECIMAL_PATTERN = /^-?\d{1,16}(?:\.\d{0,2})?$/

export class InvalidDecimalError extends Error {
  constructor(value: string) {
    super(`El importe "${value}" no es un decimal válido.`)
    this.name = 'InvalidDecimalError'
  }
}

export interface ScaledDecimal {
  /** `true` si el importe es negativo. */
  negative: boolean
  /** El importe multiplicado por 100, sin signo y exacto. */
  magnitude: bigint
  /** La parte entera del importe. */
  units: bigint
  /** Los dos decimales del importe, como número entre 0 y 99. */
  cents: number
}

/**
 * Parsea un importe decimal a su representation escalada.
 *
 * @param value - importe como string decimal, por ejemplo `"1500.50"`.
 * @returns el importe escalado.
 * @throws {InvalidDecimalError} si el string no es un decimal válido.
 */
export function parseDecimal(value: string): ScaledDecimal {
  const raw = value.trim()
  if (!DECIMAL_PATTERN.test(raw)) {
    throw new InvalidDecimalError(value)
  }

  const negative = raw.startsWith('-')
  const unsigned = negative ? raw.slice(1) : raw
  const [intPart = '', fracPart = ''] = unsigned.split('.')
  const units = BigInt(intPart)
  const cents = Number((fracPart + '00').slice(0, 2))

  return {
    negative: negative && (units > 0n || cents > 0),
    magnitude: units * 100n + BigInt(cents),
    units,
    cents,
  }
}

/**
 * Compara dos importes sin convertirlos a número.
 *
 * @param left - primer importe.
 * @param right - segundo importe.
 * @returns `-1`, `0` o `1` según el orden.
 * @throws {InvalidDecimalError} si algún importe no es válido.
 */
export function compareDecimals(left: string, right: string): -1 | 0 | 1 {
  const a = parseDecimal(left)
  const b = parseDecimal(right)

  if (a.negative !== b.negative) {
    return a.negative ? -1 : 1
  }

  const comparison = a.magnitude === b.magnitude ? 0 : a.magnitude < b.magnitude ? -1 : 1
  if (comparison === 0) {
    return 0
  }
  return a.negative ? (-comparison as -1 | 0 | 1) : comparison
}

/**
 * Calcula qué porcentaje representa `part` sobre `whole`.
 *
 * @param part - la parte (por ejemplo, lo gastado).
 * @param whole - el total (por ejemplo, el límite del presupuesto).
 * @returns el porcentaje redondeado; `0` si el total es cero.
 * @throws {InvalidDecimalError} si algún importe no es válido.
 */
export function percentOf(part: string, whole: string): number {
  const numerator = parseDecimal(part)
  const denominator = parseDecimal(whole)

  if (denominator.magnitude === 0n) {
    return 0
  }

  const scaled = numerator.magnitude * 100n
  let quotient = scaled / denominator.magnitude
  const remainder = scaled % denominator.magnitude
  if (remainder * 2n >= denominator.magnitude) {
    quotient += 1n
  }

  const negative = numerator.negative !== denominator.negative
  return Number(negative ? -quotient : quotient)
}
