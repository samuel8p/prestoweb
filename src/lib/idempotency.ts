/**
 * Claves de idempotencia.
 *
 * La API exige el header `Idempotency-Key` en las operaciones que mueven
 * dinero. La clave se genera una vez por operación y se reutiliza si hay que
 * reintentar: así un reintento no duplica el movimiento.
 */

/**
 * Genera una clave de idempotencia nueva.
 *
 * @returns un identificador único para la operación.
 */
export function createIdempotencyKey(): string {
  const cryptoApi = globalThis.crypto

  if (typeof cryptoApi?.randomUUID === 'function') {
    return cryptoApi.randomUUID()
  }

  const bytes = new Uint8Array(16)
  cryptoApi.getRandomValues(bytes)
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
}
