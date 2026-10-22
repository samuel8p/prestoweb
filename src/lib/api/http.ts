import { API_BASE_URL } from '../config'
import { apiErrorFromResponse } from './errors'

/**
 * Petición pública (sin token) contra la API.
 *
 * Se usa para los tres endpoints de tokens (login, registro y refresh): no
 * necesitan autenticación y así el cliente no depende de la sesión.
 *
 * @param path - ruta de la API.
 * @param body - cuerpo de la petición.
 * @returns la respuesta parseada.
 * @throws {ApiError} si la API responde con un error.
 */
export async function postPublic<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    let payload: unknown
    try {
      payload = await response.json()
    } catch {
      payload = null
    }
    throw apiErrorFromResponse(response.status, payload)
  }

  return (await response.json()) as T
}
