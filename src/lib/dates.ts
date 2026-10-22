/**
 * Fechas en formato ISO (`YYYY-MM-DD`).
 *
 * El backend trabaja en UTC y el rango de los reportes no puede pasar de 12
 * meses calendario, así que las fechas se arman en UTC.
 */

function toIso(date: Date): string {
  return date.toISOString().slice(0, 10)
}

/** El día de hoy en UTC. */
export function todayIso(): string {
  return toIso(new Date())
}

/** El primer día del mes actual en UTC. */
export function monthStartIso(): string {
  const now = new Date()
  return toIso(new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1)))
}

/** El último día del mes actual en UTC. */
export function monthEndIso(): string {
  const now = new Date()
  return toIso(new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 0)))
}

/**
 * El primer día del mes de hace cierta cantidad de meses.
 *
 * @param months - cuántos meses hacia atrás (0 = el mes actual).
 */
export function monthsAgoIso(months: number): string {
  const now = new Date()
  return toIso(new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - months, 1)))
}

/**
 * El rango por defecto de un reporte: los últimos 12 meses.
 *
 * Es el máximo que acepta el backend (12 meses calendario).
 */
export function defaultReportRange(): { from: string; to: string } {
  return { from: monthsAgoIso(11), to: todayIso() }
}
