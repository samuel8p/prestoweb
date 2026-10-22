import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { AppRoutes } from '../../app/routes'
import { server } from '../../test/msw/server'
import { renderWithProviders } from '../../test/render'

describe('InicioPage', () => {
  it('saluda con el nombre y muestra el saldo de la moneda activa', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    expect(screen.getAllByText('ARS 1.500,50').length).toBeGreaterThan(0)
    expect(screen.getByRole('tab', { name: 'Pesos' })).toHaveAttribute('aria-selected', 'true')

    // La otra moneda aparece al cambiar de pestaña.
    await user.click(screen.getByRole('tab', { name: 'Dólares' }))

    await waitFor(() => {
      expect(screen.getAllByText('USD 250,00').length).toBeGreaterThan(0)
    })
  })

  it('armá la superficie en L: saludo, pestañas y saldo en el mismo bloque', async () => {
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    const surface = screen.getByRole('region', { name: 'Saldo y accesos' })

    // Saludo, pestañas y saldo viven en la misma superficie.
    expect(within(surface).getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    expect(within(surface).getByRole('tab', { name: 'Pesos' })).toBeInTheDocument()
    expect(within(surface).getByRole('tab', { name: 'Dólares' })).toBeInTheDocument()
    expect(within(surface).getByText('Saldo disponible')).toBeInTheDocument()
    // La lupa y la campana están en la misma superficie.
    expect(within(surface).getByRole('button', { name: 'Buscar' })).toBeInTheDocument()
    expect(within(surface).getByRole('button', { name: 'Avisos' })).toBeInTheDocument()
  })

  it('cambia de moneda con las pestañas y con las flechas', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    const pesos = screen.getByRole('tab', { name: 'Pesos' })
    pesos.focus()
    await user.keyboard('{ArrowRight}')

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'Dólares' })).toHaveAttribute('aria-selected', 'true')
    })
  })

  it('puede ocultar el saldo', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getAllByText('ARS 1.500,50').length).toBeGreaterThan(0)
    })

    const surface = screen.getByRole('region', { name: 'Saldo y accesos' })
    await user.click(within(surface).getByRole('button', { name: 'Ocultar el saldo' }))

    await waitFor(() => {
      expect(within(surface).getByText('••••••')).toBeInTheDocument()
    })
  })

  it('tiene las tres acciones y ninguna de Retirar', async () => {
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    const surface = screen.getByRole('region', { name: 'Saldo y accesos' })
    expect(within(surface).getByRole('button', { name: /Ingresar/ })).toBeInTheDocument()
    expect(within(surface).getByRole('button', { name: /Transferir/ })).toBeInTheDocument()
    expect(within(surface).getByRole('button', { name: /Tu billetera/ })).toBeInTheDocument()
    expect(within(surface).queryByRole('button', { name: /Retirar/ })).not.toBeInTheDocument()
  })

  it('la ficha "Ingresar" abre el modal de depósito', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    const surface = screen.getByRole('region', { name: 'Saldo y accesos' })
    await user.click(within(surface).getByRole('button', { name: /Ingresar/ }))

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByRole('heading', { name: 'Ingresar dinero' })).toBeInTheDocument()
    expect(within(dialog).getByLabelText('Tipo de movimiento')).toHaveValue('deposit')
  })

  it('la ficha "Transferir" abre el modal con el buscador por alias', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    const surface = screen.getByRole('region', { name: 'Saldo y accesos' })
    await user.click(within(surface).getByRole('button', { name: /Transferir/ }))

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByRole('heading', { name: 'Transferir dinero' })).toBeInTheDocument()
    expect(within(dialog).getByLabelText('Alias del destinatario')).toBeInTheDocument()
  })

  it('la ficha "Tu billetera" muestra el alias y el identificador con copiar', async () => {
    server.use(
      http.get('*/api/v1/identity/alias/', () => HttpResponse.json({ alias: 'ana.presto' })),
    )

    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    const surface = screen.getByRole('region', { name: 'Saldo y accesos' })
    await user.click(within(surface).getByRole('button', { name: /Tu billetera/ }))

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('@ana.presto')).toBeInTheDocument()
    expect(within(dialog).getByText('22222222-2222-4222-8222-222222222222')).toBeInTheDocument()
    expect(within(dialog).getAllByRole('button', { name: /Copiar/ }).length).toBeGreaterThan(0)
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
      await screen.findByRole('button', { name: 'Abrir billetera en dólares' }),
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
