import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { AppRoutes } from '../../app/routes'
import { server } from '../../test/msw/server'
import { renderWithProviders } from '../../test/render'

describe('InvestmentsPage', () => {
  it('lista los productos de plazo fijo', async () => {
    renderWithProviders(<AppRoutes />, { route: '/inversiones', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByText('Plazo fijo de 90 días')).toBeInTheDocument()
    })
    expect(screen.getByText(/12\.00% anual/)).toBeInTheDocument()
    expect(screen.getByText('ARS 10.000,00')).toBeInTheDocument()
  })

  it('muestra las posiciones con el interés esperado', async () => {
    renderWithProviders(<AppRoutes />, { route: '/inversiones', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByText('Interés esperado')).toBeInTheDocument()
    })
    expect(screen.getByText('ARS 50.000,00')).toBeInTheDocument()
    expect(screen.getByText('ARS 1.479,45')).toBeInTheDocument()
  })

  it('abre una posición con el header Idempotency-Key', async () => {
    let idempotencyKey: string | null = null
    server.use(
      http.post('*/api/v1/investments/positions/', ({ request }) => {
        idempotencyKey = request.headers.get('Idempotency-Key')
        return HttpResponse.json(
          {
            id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
            product: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
            amount: '60000.00',
            status: 'active',
            opened_at: '2026-10-22T10:00:00Z',
            maturity_date: '2027-01-20',
            interest_amount: '1775.34',
          },
          { status: 201 },
        )
      }),
    )

    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/inversiones', session: 'authenticated' })

    await user.click(await screen.findByRole('button', { name: 'Invertir' }))
    const dialog = await screen.findByRole('dialog')
    await user.type(within(dialog).getByLabelText('Importe a invertir'), '60000.00')
    await user.click(within(dialog).getByRole('button', { name: 'Invertir' }))

    await waitFor(() => {
      expect(idempotencyKey).toBeTruthy()
    })
  })

  it('valida el importe mínimo del producto', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/inversiones', session: 'authenticated' })

    await user.click(await screen.findByRole('button', { name: 'Invertir' }))
    const dialog = await screen.findByRole('dialog')
    await user.type(within(dialog).getByLabelText('Importe a invertir'), '100')
    await user.click(within(dialog).getByRole('button', { name: 'Invertir' }))

    await waitFor(() => {
      expect(
        screen.getByText('El importe mínimo de este producto es 10000.00 ARS.'),
      ).toBeInTheDocument()
    })
  })
})
