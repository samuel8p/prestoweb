import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { AppRoutes } from '../../app/routes'
import { server } from '../../test/msw/server'
import { renderWithProviders } from '../../test/render'

describe('BudgetsPage', () => {
  it('muestra las categorías y los presupuestos del mes', async () => {
    renderWithProviders(<AppRoutes />, { route: '/presupuestos', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getAllByText('Almacenamiento').length).toBeGreaterThan(0)
    })
    expect(screen.getByRole('heading', { name: 'Presupuestos del mes' })).toBeInTheDocument()
  })

  it('muestra el estado del presupuesto: gastado, disponible y alerta', async () => {
    renderWithProviders(<AppRoutes />, { route: '/presupuestos', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByText('Gastado')).toBeInTheDocument()
    })
    expect(screen.getByText('Disponible')).toBeInTheDocument()
    expect(screen.getByText('Umbral')).toBeInTheDocument()
    expect(screen.getByText('ARS 50.000,00')).toBeInTheDocument()
    expect(screen.getByText('ARS 150.000,00')).toBeInTheDocument()
  })

  it('crea una categoría', async () => {
    let created = ''
    server.use(
      http.post('*/api/v1/budgets/categories/', async ({ request }) => {
        const body = (await request.json()) as { name: string }
        created = body.name
        return HttpResponse.json(
          {
            id: 'dddddddd-dddd-4ddd-8ddd-dddddddddd02',
            name: created,
            created_at: '2026-10-10T10:00:00Z',
          },
          { status: 201 },
        )
      }),
    )

    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/presupuestos', session: 'authenticated' })

    await user.click(await screen.findByRole('button', { name: 'Nueva categoría' }))
    const dialog = await screen.findByRole('dialog')
    await user.type(within(dialog).getByLabelText('Nombre de la categoría'), 'Transporte')
    await user.click(within(dialog).getByRole('button', { name: 'Crear categoría' }))

    await waitFor(() => {
      expect(created).toBe('Transporte')
    })
  })

  it('crea un presupuesto con su límite y umbral', async () => {
    let payload: unknown = null
    server.use(
      http.post('*/api/v1/budgets/', async ({ request }) => {
        payload = await request.json()
        return HttpResponse.json(
          {
            id: 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeee02',
            category: {
              id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
              name: 'Almacenamiento',
              created_at: '2026-10-10T10:00:00Z',
            },
            period: 'monthly',
            limit_amount: '100000.00',
            currency: 'ARS',
            alert_threshold: 90,
            created_at: '2026-10-10T10:00:00Z',
          },
          { status: 201 },
        )
      }),
    )

    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/presupuestos', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Nuevo presupuesto' })).toBeEnabled()
    })
    await user.click(screen.getByRole('button', { name: 'Nuevo presupuesto' }))
    const dialog = await screen.findByRole('dialog')
    await user.type(within(dialog).getByLabelText('Límite mensual'), '100000.00')
    await user.clear(within(dialog).getByLabelText('Umbral de alerta (%)'))
    await user.type(within(dialog).getByLabelText('Umbral de alerta (%)'), '90')
    await user.click(within(dialog).getByRole('button', { name: 'Crear presupuesto' }))

    await waitFor(() => {
      expect(payload).toMatchObject({
        limit_amount: '100000.00',
        currency: 'ARS',
        alert_threshold: 90,
      })
    })
  })

  it('categoriza un movimiento del ledger', async () => {
    let payload: unknown = null
    server.use(
      http.post('*/api/v1/budgets/expenses/', async ({ request }) => {
        payload = await request.json()
        return HttpResponse.json(
          {
            id: 'ffffffff-ffff-4fff-8fff-fffffffffff02',
            category: {
              id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
              name: 'Almacenamiento',
              created_at: '2026-10-10T10:00:00Z',
            },
            ledger_transaction_id: '44444444-4444-4444-8444-444444444444',
            created_at: '2026-10-22T10:00:00Z',
          },
          { status: 201 },
        )
      }),
    )

    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/presupuestos', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Categorizar movimiento' })).toBeEnabled()
    })
    await user.click(screen.getByRole('button', { name: 'Categorizar movimiento' }))
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Categorizar' }))

    await waitFor(() => {
      expect(payload).toMatchObject({
        category_id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
        ledger_transaction_id: '44444444-4444-4444-8444-444444444444',
      })
    })
  })
})
