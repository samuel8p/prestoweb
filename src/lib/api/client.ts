import type { ApiError } from './errors'
import { apiErrorFromResponse } from './errors'

export type QueryValue = string | number | boolean | undefined | null

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  query?: Record<string, QueryValue>
  headers?: Record<string, string>
  signal?: AbortSignal
  /** `false` para las peticiones públicas (por ejemplo `/api/v1/meta/`). */
  auth?: boolean
}

export interface ApiClientOptions {
  baseUrl: string
  /** Devuelve el access token en memoria, o `null` si no hay sesión. */
  getAccessToken?: () => string | null
  /** Renueva el access token. Devuelve el token nuevo o `null` si no se pudo. */
  refreshAccessToken?: () => Promise<string | null>
  /** Se llama cuando la sesión se cae y ya no se pudo renovar. */
  onSessionExpired?: () => void
}

export interface DownloadedFile {
  blob: Blob
  filename: string
}

function buildUrl(baseUrl: string, path: string, query?: Record<string, QueryValue>): string {
  const base = `${baseUrl.replace(/\/+$/, '')}${path.startsWith('/') ? path : `/${path}`}`
  if (!query) {
    return base
  }

  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') {
      continue
    }
    params.append(key, String(value))
  }
  const search = params.toString()
  return search ? `${base}?${search}` : base
}

function filenameFromContentDisposition(header: string | null): string {
  if (!header) {
    return 'reporte.csv'
  }
  const match = /filename="?([^";]+)"?/.exec(header)
  return match?.[1] ?? 'reporte.csv'
}

/**
 * Cliente HTTP de la API de Presto.
 *
 * Un solo lugar donde se arman las peticiones: agrega el token, renueva la
 * sesión ante un 401 y traduce los errores del backend a `ApiError`.
 */
export class ApiClient {
  private readonly baseUrl: string
  private readonly getAccessToken?: () => string | null
  private readonly refreshAccessToken?: () => Promise<string | null>
  private readonly onSessionExpired?: () => void

  constructor(options: ApiClientOptions) {
    this.baseUrl = options.baseUrl
    this.getAccessToken = options.getAccessToken
    this.refreshAccessToken = options.refreshAccessToken
    this.onSessionExpired = options.onSessionExpired
  }

  async get<T>(path: string, options: Omit<RequestOptions, 'method' | 'body'> = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: 'GET' })
  }

  async post<T>(
    path: string,
    body?: unknown,
    options: Omit<RequestOptions, 'method' | 'body'> = {},
  ): Promise<T> {
    return this.request<T>(path, { ...options, method: 'POST', body })
  }

  async put<T>(
    path: string,
    body?: unknown,
    options: Omit<RequestOptions, 'method' | 'body'> = {},
  ): Promise<T> {
    return this.request<T>(path, { ...options, method: 'PUT', body })
  }

  async patch<T>(
    path: string,
    body?: unknown,
    options: Omit<RequestOptions, 'method' | 'body'> = {},
  ): Promise<T> {
    return this.request<T>(path, { ...options, method: 'PATCH', body })
  }

  async delete<T>(path: string, options: Omit<RequestOptions, 'method' | 'body'> = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: 'DELETE' })
  }

  /**
   * Baja un archivo CSV con el token de la sesión.
   *
   * @param path - ruta del reporte.
   * @param options - query params (la API espera `export=csv`).
   * @returns el archivo y el nombre que sugirió el backend.
   */
  async downloadCsv(
    path: string,
    options: Omit<RequestOptions, 'method' | 'body'> = {},
  ): Promise<DownloadedFile> {
    const response = await this.fetchWithSession(path, { ...options, method: 'GET' })

    if (!response.ok) {
      throw await this.buildError(response)
    }

    return {
      blob: await response.blob(),
      filename: filenameFromContentDisposition(response.headers.get('Content-Disposition')),
    }
  }

  private async request<T>(path: string, options: RequestOptions): Promise<T> {
    const response = await this.fetchWithSession(path, options)

    if (!response.ok) {
      throw await this.buildError(response)
    }

    if (response.status === 204) {
      return undefined as T
    }

    const contentType = response.headers.get('Content-Type') ?? ''
    if (!contentType.includes('application/json')) {
      return (await response.text()) as T
    }

    return (await response.json()) as T
  }

  private async fetchWithSession(path: string, options: RequestOptions): Promise<Response> {
    const useAuth = options.auth !== false
    const token = useAuth ? (this.getAccessToken?.() ?? null) : null

    const response = await this.fetchOnce(path, options, token)

    if (response.status !== 401 || !useAuth || !this.refreshAccessToken) {
      return response
    }

    const newToken = await this.refreshAccessToken()
    if (!newToken) {
      this.onSessionExpired?.()
      return response
    }

    return this.fetchOnce(path, options, newToken)
  }

  private async fetchOnce(
    path: string,
    options: RequestOptions,
    token: string | null,
  ): Promise<Response> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      ...options.headers,
    }
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }
    if (options.body !== undefined) {
      headers['Content-Type'] = 'application/json'
    }

    return fetch(buildUrl(this.baseUrl, path, options.query), {
      method: options.method ?? 'GET',
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    })
  }

  private async buildError(response: Response): Promise<ApiError> {
    let body: unknown
    const contentType = response.headers.get('Content-Type') ?? ''
    try {
      body = contentType.includes('application/json')
        ? await response.json()
        : await response.text()
    } catch {
      body = null
    }
    return apiErrorFromResponse(response.status, body)
  }
}
