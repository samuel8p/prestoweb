import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { AppRoutes } from '../../app/routes'
import { server } from '../../test/msw/server'
import { renderWithProviders } from '../../test/render'

describe('ReportsPage', () => {
  it('muestra el reporte de movimientos de la moneda elegida', async () => {
    renderWithProviders(<AppRoutes />, { route: '/reportes', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Movimientos del período' })).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.getByText('ARS 1.500,50')).toBeInTheDocument()
    })
  })

  it('cambia de reporte con las pestañas', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/reportes', session: 'authenticated' })

    await user.click(await screen.findByRole('tab', { name: 'Gasto por categoría' }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Gasto por categoría' })).toBeInTheDocument()
    })
    expect(screen.getByText('Almacenamiento')).toBeInTheDocument()
  })

  it('muestra el resumen de préstamos', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/reportes', session: 'authenticated' })

    await user.click(await screen.findByRole('tab', { name: 'Préstamos' }))

    await waitFor(() => {
      expect(screen.getByText('Como prestatario')).toBeInTheDocument()
    })
    expect(screen.getByText('Como prestamista')).toBeInTheDocument()
  })

  it('descarga el CSV con la moneda y el rango', async () => {
    const createObjectURL = vi.fn(() => 'blob:mock')
    const revokeObjectURL = vi.fn()
    // Se definen solo los dos métodos: reemplazar el constructor `URL` rompe
    // el router.
    Object.defineProperty(URL, 'createObjectURL', { value: createObjectURL, configurable: true })
    Object.defineProperty(URL, 'revokeObjectURL', { value: revokeObjectURL, configurable: true })

    let requestedUrl = ''
    server.use(
      http.get('*/api/v1/reports/spending/', ({ request }) => {
        requestedUrl = request.url
        if (new URL(request.url).searchParams.get('export') !== 'csv') {
          return HttpResponse.json({
            currency: 'ARS',
            from_date: '2026-10-01',
            to_date: '2026-10-31',
            total: '50000.00',
            categories: [],
          })
        }
        return HttpResponse.text('category_id,amount\n1,2\n', {
          headers: {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': 'attachment; filename="reporte-gasto.csv"',
          },
        })
      }),
    )

    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/reportes', session: 'authenticated' })

    await user.click(await screen.findByRole('tab', { name: 'Gasto por categoría' }))
    await user.click(screen.getByRole('button', { name: 'Descargar CSV' }))

    await waitFor(() => {
      expect(requestedUrl).toContain('export=csv')
    })
    expect(requestedUrl).toContain('currency=ARS')
    expect(createObjectURL).toHaveBeenCalled()
  })
})
