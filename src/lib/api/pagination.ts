/**
 * Utilidades de paginación.
 *
 * El backend devuelve en `next` la URL completa de la página siguiente. Los
 * movimientos del ledger usan paginación por cursor: de esa URL solo hace
 * falta el parámetro `cursor`.
 */

/**
 * Saca el cursor de la URL de la página siguiente.
 *
 * @param url - la URL que devuelve la API en `next`.
 * @returns el cursor, o `undefined` si no hay página siguiente.
 */
export function cursorFromUrl(url: string | null | undefined): string | undefined {
  if (!url) {
    return undefined
  }

  try {
    const parsed = new URL(url, 'http://localhost')
    return parsed.searchParams.get('cursor') ?? undefined
  } catch {
    return undefined
  }
}
