import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { AppRoutes } from '../../app/routes'
import { server } from '../../test/msw/server'
import { renderWithProviders } from '../../test/render'

describe('MarketplacePage', () => {
  it('lista las ofertas del marketplace', async () => {
    renderWithProviders(<AppRoutes />, { route: '/ofertas', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByText('ARS 100.000,00')).toBeInTheDocument()
    })
    expect(screen.getByText('24,00% anual · 12 meses')).toBeInTheDocument()
  })

  it('filtra por moneda', async () => {
    const currencies: string[] = []
    server.use(
      http.get('*/api/v1/matching/offers/', ({ request }) => {
        currencies.push(new URL(request.url).searchParams.get('currency') ?? '')
        return HttpResponse.json({ count: 0, next: null, previous: null, results: [] })
      }),
    )

    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/ofertas', session: 'authenticated' })

    await user.selectOptions(await screen.findByLabelText('Moneda'), 'USD')
    await user.click(screen.getByRole('button', { name: 'Buscar ofertas' }))

    await waitFor(() => {
      expect(currencies.at(-1)).toBe('USD')
    })
  })

  it('publica una oferta', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/ofertas', session: 'authenticated' })

    const openButtons = await screen.findAllByRole('button', { name: 'Publicar oferta' })
    await user.click(openButtons[0]!)

    const dialog = await screen.findByRole('dialog')
    await user.type(within(dialog).getByLabelText('Importe'), '50000.00')
    await user.type(within(dialog).getByLabelText('Tasa anual (TNA)'), '18.00')
    await user.type(within(dialog).getByLabelText('Plazo en meses'), '6')

    await user.click(within(dialog).getByRole('button', { name: 'Publicar oferta' }))

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })

  it('acepta una oferta y abre el préstamo', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/ofertas', session: 'authenticated' })

    await user.click(await screen.findByRole('button', { name: 'Aceptar' }))
    await user.click(screen.getByRole('button', { name: 'Aceptar y recibir' }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Detalle del préstamo' })).toBeInTheDocument()
    })
  })
})
