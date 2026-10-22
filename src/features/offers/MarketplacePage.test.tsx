import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { AppRoutes } from '../../app/routes'
import { server } from '../../test/msw/server'
import { renderWithProviders } from '../../test/render'

/** El buscador del marketplace arranca oculto: hay que pedirlo. */
async function openSearch(user: ReturnType<typeof userEvent.setup>) {
  const button = await screen.findByRole('button', { name: 'Buscar ofertas' })
  await user.click(button)
  await waitFor(() => {
    expect(screen.getByLabelText('Moneda')).toBeInTheDocument()
  })
}

describe('MarketplacePage', () => {
  it('arranca con las ofertas propias y sin el formulario de búsqueda', async () => {
    renderWithProviders(<AppRoutes />, {
      route: '/prestamos?vista=ofertas',
      session: 'authenticated',
    })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Mis ofertas' })).toBeInTheDocument()
    })
    expect(screen.queryByLabelText('Moneda')).not.toBeInTheDocument()
  })

  it('revela el formulario al apretar "Buscar ofertas"', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, {
      route: '/prestamos?vista=ofertas',
      session: 'authenticated',
    })

    await openSearch(user)

    expect(screen.getByLabelText('Moneda')).toBeInTheDocument()
    expect(screen.getByText('ARS 100.000,00')).toBeInTheDocument()
    expect(screen.getByText('24,00% anual · 12 meses')).toBeInTheDocument()
  })

  it('filtra por moneda', async () => {
    const user = userEvent.setup()
    const currencies: string[] = []
    server.use(
      http.get('*/api/v1/matching/offers/', ({ request }) => {
        currencies.push(new URL(request.url).searchParams.get('currency') ?? '')
        return HttpResponse.json({ count: 0, next: null, previous: null, results: [] })
      }),
    )

    renderWithProviders(<AppRoutes />, {
      route: '/prestamos?vista=ofertas',
      session: 'authenticated',
    })

    await openSearch(user)
    await user.selectOptions(screen.getByLabelText('Moneda'), 'USD')
    await user.click(screen.getByRole('button', { name: 'Buscar ofertas' }))

    await waitFor(() => {
      expect(currencies.at(-1)).toBe('USD')
    })
  })

  it('publica una oferta', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, {
      route: '/prestamos?vista=ofertas',
      session: 'authenticated',
    })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Mis ofertas' })).toBeInTheDocument()
    })

    const publishButtons = screen.getAllByRole('button', { name: 'Publicar oferta' })
    await user.click(publishButtons[0]!)

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
    renderWithProviders(<AppRoutes />, {
      route: '/prestamos?vista=ofertas',
      session: 'authenticated',
    })

    await openSearch(user)
    await user.click(await screen.findByRole('button', { name: 'Aceptar' }))
    await user.click(screen.getByRole('button', { name: 'Aceptar y recibir' }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Detalle del préstamo' })).toBeInTheDocument()
    })
  })
})
