import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { ApiError } from './errors'
import { ApiClient } from './client'
import { server } from '../../test/msw/server'

const BASE_URL = 'http://api.test'

function createClient(overrides: Partial<ConstructorParameters<typeof ApiClient>[0]> = {}) {
  return new ApiClient({
    baseUrl: BASE_URL,
    ...overrides,
  })
}

describe('ApiClient', () => {
  it('arma la URL con los query params y descarta los vacíos', async () => {
    let requestedUrl = ''
    server.use(
      http.get('http://api.test/api/v1/reports/spending/', ({ request }) => {
        requestedUrl = request.url
        return HttpResponse.json({ ok: true })
      }),
    )

    const client = createClient()
    await client.get('/api/v1/reports/spending/', {
      query: { currency: 'ARS', from: undefined, to: null },
    })

    expect(requestedUrl).toBe('http://api.test/api/v1/reports/spending/?currency=ARS')
  })

  it('manda el token de acceso cuando hay sesión', async () => {
    let authorization: string | null = null
    server.use(
      http.get('http://api.test/api/v1/auth/me/', ({ request }) => {
        authorization = request.headers.get('Authorization')
        return HttpResponse.json({ id: '1' })
      }),
    )

    const client = createClient({ getAccessToken: () => 'token-123' })
    await client.get('/api/v1/auth/me/')

    expect(authorization).toBe('Bearer token-123')
  })

  it('no manda el token cuando la petición es pública', async () => {
    let authorization: string | null = 'sin-header'
    server.use(
      http.get('http://api.test/api/v1/meta/', ({ request }) => {
        authorization = request.headers.get('Authorization')
        return HttpResponse.json({ mode: 'demo', simulated_money: true })
      }),
    )

    const client = createClient({ getAccessToken: () => 'token-123' })
    await client.get('/api/v1/meta/', { auth: false })

    expect(authorization).toBeNull()
  })

  it('envía el cuerpo en JSON', async () => {
    let body: unknown = null
    server.use(
      http.post('http://api.test/api/v1/ledger/accounts/', async ({ request }) => {
        body = await request.json()
        return HttpResponse.json({ id: '1' }, { status: 201 })
      }),
    )

    const client = createClient()
    await client.post('/api/v1/ledger/accounts/', { currency: 'ARS' })

    expect(body).toEqual({ currency: 'ARS' })
  })

  it('renueva el token ante un 401 y reintenta la petición', async () => {
    let attempts = 0
    server.use(
      http.get('http://api.test/api/v1/auth/me/', ({ request }) => {
        attempts += 1
        if (request.headers.get('Authorization') === 'Bearer token-nuevo') {
          return HttpResponse.json({ id: '1' })
        }
        return HttpResponse.json(
          { error: { code: 'not_authenticated', message: 'Token inválido.' } },
          { status: 401 },
        )
      }),
    )

    const refreshAccessToken = vi.fn(async () => 'token-nuevo')
    const client = createClient({ getAccessToken: () => 'token-viejo', refreshAccessToken })

    const result = await client.get<{ id: string }>('/api/v1/auth/me/')

    expect(result).toEqual({ id: '1' })
    expect(refreshAccessToken).toHaveBeenCalledTimes(1)
    expect(attempts).toBe(2)
  })

  it('cierra la sesión cuando la renovación falla', async () => {
    server.use(
      http.get('http://api.test/api/v1/auth/me/', () =>
        HttpResponse.json(
          { error: { code: 'not_authenticated', message: 'Token inválido.' } },
          { status: 401 },
        ),
      ),
    )

    const onSessionExpired = vi.fn()
    const client = createClient({
      getAccessToken: () => 'token-viejo',
      refreshAccessToken: async () => null,
      onSessionExpired,
    })

    await expect(client.get('/api/v1/auth/me/')).rejects.toBeInstanceOf(ApiError)
    expect(onSessionExpired).toHaveBeenCalledTimes(1)
  })

  it('no intenta renovar más de una vez', async () => {
    server.use(
      http.get('http://api.test/api/v1/auth/me/', () =>
        HttpResponse.json(
          { error: { code: 'not_authenticated', message: 'Token inválido.' } },
          { status: 401 },
        ),
      ),
    )

    const refreshAccessToken = vi.fn(async () => 'token-nuevo')
    const client = createClient({ getAccessToken: () => 'token-viejo', refreshAccessToken })

    await expect(client.get('/api/v1/auth/me/')).rejects.toBeInstanceOf(ApiError)
    expect(refreshAccessToken).toHaveBeenCalledTimes(1)
  })

  it('lanza un ApiError con los errores por campo', async () => {
    server.use(
      http.post('http://api.test/api/v1/ledger/transactions/', () =>
        HttpResponse.json(
          {
            error: {
              code: 'validation_error',
              message: 'Los datos enviados no son válidos.',
              details: { amount: ['A valid number is required.'] },
            },
          },
          { status: 400 },
        ),
      ),
    )

    const client = createClient()

    await expect(client.post('/api/v1/ledger/transactions/', {})).rejects.toMatchObject({
      status: 400,
      code: 'validation_error',
      fieldErrors: { amount: ['Ingresá un número válido.'] },
    })
  })

  it('no rompe cuando la respuesta de error no es JSON', async () => {
    server.use(
      http.get('http://api.test/api/v1/auth/me/', () =>
        HttpResponse.text('<html>Internal Server Error</html>', { status: 500 }),
      ),
    )

    const client = createClient()

    await expect(client.get('/api/v1/auth/me/')).rejects.toMatchObject({ status: 500 })
  })

  it('baja el CSV con el nombre del archivo que manda el backend', async () => {
    server.use(
      http.get('http://api.test/api/v1/reports/spending/', () =>
        HttpResponse.text('a,b\n1,2\n', {
          headers: {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': 'attachment; filename="reporte-gasto.csv"',
          },
        }),
      ),
    )

    const client = createClient()
    const file = await client.downloadCsv('/api/v1/reports/spending/', {
      query: { currency: 'ARS', export: 'csv' },
    })

    expect(file.filename).toBe('reporte-gasto.csv')
    expect(await file.blob.text()).toBe('a,b\n1,2\n')
  })
})
