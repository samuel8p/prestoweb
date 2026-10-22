import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { AppRoutes } from '../../app/routes'
import { server } from '../../test/msw/server'
import { renderWithProviders } from '../../test/render'

describe('NotificationsPage', () => {
  it('lista los avisos con su estado', async () => {
    renderWithProviders(<AppRoutes />, { route: '/avisos', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getAllByText('Cuota por vencer').length).toBeGreaterThan(0)
    })
    expect(screen.getByText('Enviado')).toBeInTheDocument()
  })

  it('muestra las preferencias por tipo de aviso', async () => {
    renderWithProviders(<AppRoutes />, { route: '/avisos', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByLabelText('Cuota vencida')).toBeInTheDocument()
    })
    expect(screen.getByLabelText('Alerta de presupuesto')).toBeChecked()
  })

  it('desactiva un tipo de aviso', async () => {
    let payload: unknown = null
    server.use(
      http.put('*/api/v1/notifications/preferences/', async ({ request }) => {
        payload = await request.json()
        return HttpResponse.json({ event_type: 'investment_settled', enabled: false })
      }),
    )

    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/avisos', session: 'authenticated' })

    const checkbox = await screen.findByLabelText('Inversión liquidada')
    await user.click(checkbox)

    await waitFor(() => {
      expect(payload).toEqual({ event_type: 'investment_settled', enabled: false })
    })
  })
})
