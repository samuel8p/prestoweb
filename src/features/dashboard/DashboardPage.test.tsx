import { screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { AppRoutes } from '../../app/routes'
import { server } from '../../test/msw/server'
import { renderWithProviders } from '../../test/render'

describe('DashboardPage', () => {
  it('muestra el saldo de cada billetera', async () => {
    renderWithProviders(<AppRoutes />, { route: '/panel', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByText('ARS 1.500,50')).toBeInTheDocument()
    })
    expect(screen.getByText('USD 250,00')).toBeInTheDocument()
  })

  it('muestra los últimos movimientos y los avisos', async () => {
    renderWithProviders(<AppRoutes />, { route: '/panel', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByText('Depósito de prueba')).toBeInTheDocument()
    })
    expect(screen.getByRole('heading', { name: 'Últimos movimientos' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Avisos' })).toBeInTheDocument()
    expect(screen.getByText('Cuota por vencer')).toBeInTheDocument()
  })

  it('avisa cuando no hay billeteras', async () => {
    server.use(
      http.get('*/api/v1/ledger/accounts/', () =>
        HttpResponse.json({ count: 0, next: null, previous: null, results: [] }),
      ),
    )

    renderWithProviders(<AppRoutes />, { route: '/panel', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByText('Todavía no tenés billeteras')).toBeInTheDocument()
    })
  })
})
