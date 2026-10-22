import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { AppRoutes } from '../../app/routes'
import { server } from '../../test/msw/server'
import { renderWithProviders } from '../../test/render'

describe('LoansPage', () => {
  it('lista los préstamos con el rol de cada uno', async () => {
    renderWithProviders(<AppRoutes />, { route: '/prestamos', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByText('ARS 100.000,00')).toBeInTheDocument()
    })
    expect(screen.getByText('Como prestatario')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Mis préstamos' })).toBeInTheDocument()
  })

  it('paga una cuota del préstamo', async () => {
    let paidNumber = ''
    server.use(
      http.post('*/api/v1/loans/:loanId/installments/:number/pay/', ({ params }) => {
        paidNumber = String(params.number)
        return HttpResponse.json({
          id: '88888888-8888-4888-8888-888888888881',
          number: 1,
          due_date: '2026-11-20',
          principal_amount: '8000.00',
          interest_amount: '2000.00',
          amount: '10000.00',
          status: 'paid',
          paid_at: '2026-10-25T10:00:00Z',
        })
      }),
    )

    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, {
      route: '/prestamos/77777777-7777-4777-8777-777777777777',
      session: 'authenticated',
    })

    await user.click(await screen.findByRole('button', { name: 'Pagar' }))

    await waitFor(() => {
      expect(paidNumber).toBe('1')
    })
  })

  it('muestra el detalle con las cuotas', async () => {
    renderWithProviders(<AppRoutes />, {
      route: '/prestamos/77777777-7777-4777-8777-777777777777',
      session: 'authenticated',
    })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Detalle del préstamo' })).toBeInTheDocument()
    })
    // La cuota se muestra en una tabla: número, vencimiento y total.
    expect(await screen.findByText('20/11/2026')).toBeInTheDocument()
    expect(screen.getByText('ARS 10.000,00')).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Cuota' })).toBeInTheDocument()
  })
})
