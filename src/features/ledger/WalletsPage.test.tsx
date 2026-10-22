import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { AppRoutes } from '../../app/routes'
import { server } from '../../test/msw/server'
import { renderWithProviders } from '../../test/render'

describe('WalletsPage', () => {
  it('crea un movimiento con el header Idempotency-Key', async () => {
    let idempotencyKey: string | null = null
    let body: unknown = null

    server.use(
      http.post('*/api/v1/ledger/transactions/', async ({ request }) => {
        idempotencyKey = request.headers.get('Idempotency-Key')
        body = await request.json()
        return HttpResponse.json(
          {
            id: '44444444-4444-4444-8444-444444444444',
            type: 'deposit',
            idempotency_key: 'key',
            created_by_user_id: '11111111-1111-4111-8111-111111111111',
            destination_account_id: null,
            occurred_at: '2026-10-20T12:00:00Z',
            description: '',
            reverses: null,
            created_at: '2026-10-20T12:00:00Z',
          },
          { status: 201 },
        )
      }),
    )

    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/billetera', session: 'authenticated' })

    await user.click(await screen.findByRole('button', { name: 'Nuevo movimiento' }))
    await user.type(await screen.findByLabelText('Importe'), '250.75')
    await user.click(screen.getByRole('button', { name: 'Confirmar' }))

    await waitFor(() => {
      expect(idempotencyKey).toBeTruthy()
    })
    expect(body).toMatchObject({ type: 'deposit', currency: 'ARS', amount: '250.75' })
  })

  it('pide la cuenta de destino en una transferencia', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/billetera', session: 'authenticated' })

    await user.click(await screen.findByRole('button', { name: 'Nuevo movimiento' }))
    await user.selectOptions(await screen.findByLabelText('Tipo de movimiento'), 'transfer')

    await waitFor(() => {
      expect(screen.getByLabelText('ID de la cuenta de destino')).toBeInTheDocument()
    })
  })

  it('valida que el importe sea mayor que cero', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/billetera', session: 'authenticated' })

    await user.click(await screen.findByRole('button', { name: 'Nuevo movimiento' }))
    await user.type(await screen.findByLabelText('Importe'), '0')
    await user.click(screen.getByRole('button', { name: 'Confirmar' }))

    await waitFor(() => {
      expect(screen.getByText('El importe tiene que ser mayor que cero.')).toBeInTheDocument()
    })
  })

  it('avisa cuando falta la verificación KYC', async () => {
    server.use(
      http.post('*/api/v1/ledger/transactions/', () =>
        HttpResponse.json(
          {
            error: {
              code: 'permission_denied',
              message: 'Necesitás completar la verificación KYC para realizar esta operación.',
              details: {},
            },
          },
          { status: 403 },
        ),
      ),
    )

    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/billetera', session: 'authenticated' })

    await user.click(await screen.findByRole('button', { name: 'Nuevo movimiento' }))
    await user.type(await screen.findByLabelText('Importe'), '100')
    await user.click(screen.getByRole('button', { name: 'Confirmar' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Tu cuenta aún no fue verificada (KYC)')
    })
  })

  it('abre el formulario de billetera nueva', async () => {
    server.use(
      http.get('*/api/v1/ledger/accounts/', () =>
        HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: '22222222-2222-4222-8222-222222222222',
              user_id: '11111111-1111-4111-8111-111111111111',
              currency: 'ARS',
              kind: 'user_wallet',
              balance: '1500.50',
              created_at: '2026-10-01T10:00:00Z',
            },
          ],
        }),
      ),
    )

    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/billetera', session: 'authenticated' })

    await user.click(await screen.findByRole('radio', { name: 'Dólares (USD)' }))
    await user.click(await screen.findByRole('button', { name: 'Abrir billetera USD' }))

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
    expect(screen.getByLabelText('Moneda de la billetera')).toBeInTheDocument()
  })

  it('filtra los movimientos por la moneda elegida', async () => {
    const currencies: string[] = []
    server.use(
      http.get('*/api/v1/reports/movements/', ({ request }) => {
        currencies.push(new URL(request.url).searchParams.get('currency') ?? '')
        return HttpResponse.json({ count: 0, next: null, previous: null, results: [] })
      }),
    )

    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/billetera', session: 'authenticated' })

    await user.click(await screen.findByRole('radio', { name: 'Dólares (USD)' }))

    await waitFor(() => {
      expect(currencies.at(-1)).toBe('USD')
    })
  })
})
