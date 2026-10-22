import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { AppRoutes } from '../../app/routes'
import { server } from '../../test/msw/server'
import { renderWithProviders } from '../../test/render'

describe('InicioPage', () => {
  it('saluda con el nombre y muestra los saldos de las dos monedas', async () => {
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    await waitFor(() => {
      expect(screen.getAllByText('ARS 1.500,50').length).toBeGreaterThan(0)
    })
    expect(screen.getAllByText('USD 250,00').length).toBeGreaterThan(0)
    expect(screen.getByRole('tab', { name: 'Pesos' })).toHaveAttribute('aria-selected', 'true')
  })

  it('puede ocultar los saldos', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getAllByText('ARS 1.500,50').length).toBeGreaterThan(0)
    })

    await user.click(screen.getByRole('button', { name: 'Ocultar los saldos' }))

    // Solo se tapan los saldos: los movimientos siguen mostrando el importe.
    const balance = screen.getByRole('region', { name: 'Saldo en Pesos' })
    await waitFor(() => {
      expect(within(balance).getByText('••••••')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: 'Mostrar los saldos' })).toBeInTheDocument()
  })

  it('la ficha "Ingresar" abre el modal de depósito', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /Ingresar/ }))

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByRole('heading', { name: 'Ingresar dinero' })).toBeInTheDocument()
    expect(within(dialog).getByLabelText('Tipo de movimiento')).toHaveValue('deposit')
  })

  it('la ficha "Transferir" abre el modal de transferencia', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /Transferir/ }))

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByLabelText('Tipo de movimiento')).toHaveValue('transfer')
  })

  it('la ficha "Retirar" abre el modal de retiro', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /Retirar/ }))

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByLabelText('Tipo de movimiento')).toHaveValue('withdrawal')
  })

  it('la ficha "Tu billetera" muestra el identificador para copiar', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /Tu billetera/ }))

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByRole('heading', { name: 'Tu billetera' })).toBeInTheDocument()
    expect(within(dialog).getByText('22222222-2222-4222-8222-222222222222')).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Copiar identificador' })).toBeInTheDocument()
  })

  it('ofrece abrir una billetera en la moneda que falta', async () => {
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
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    // Sin billetera en USD.
    await user.click(await screen.findByRole('tab', { name: 'Dólares' }))

    expect(
      await screen.findByRole('button', { name: 'Abrir billetera en Dólares' }),
    ).toBeInTheDocument()
  })

  it('enlaza a los movimientos recientes con el historial', async () => {
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    expect(screen.getByRole('link', { name: 'Ver todos' })).toHaveAttribute('href', '/billetera')
  })
})
