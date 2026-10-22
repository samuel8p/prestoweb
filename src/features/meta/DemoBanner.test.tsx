import { screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { renderWithProviders } from '../../test/render'
import { server } from '../../test/msw/server'
import { DemoBanner } from './DemoBanner'

describe('DemoBanner', () => {
  it('muestra el cartel cuando la instancia está en modo demo', async () => {
    renderWithProviders(<DemoBanner />)

    await waitFor(() => {
      expect(screen.getByText('Demo: el dinero es simulado')).toBeInTheDocument()
    })
  })

  it('no muestra el cartel cuando la instancia no está en modo demo', async () => {
    server.use(
      http.get('*/api/v1/meta/', () =>
        HttpResponse.json({ mode: 'normal', simulated_money: false }),
      ),
    )

    renderWithProviders(<DemoBanner />)

    await waitFor(() => {
      expect(screen.queryByText('Demo: el dinero es simulado')).not.toBeInTheDocument()
    })
  })

  it('no rompe cuando el endpoint de modo falla', async () => {
    server.use(
      http.get('*/api/v1/meta/', () => HttpResponse.json({ detail: 'boom' }, { status: 500 })),
    )

    renderWithProviders(<DemoBanner />)

    await waitFor(() => {
      expect(screen.queryByText('Demo: el dinero es simulado')).not.toBeInTheDocument()
    })
  })
})
