import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { AppRoutes } from '../../app/routes'
import { renderWithProviders } from '../../test/render'

describe('buscador global', () => {
  it('se abre con Ctrl+K', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    await user.keyboard('{Control>}k{/Control}')

    expect(await screen.findByRole('dialog', { name: 'Buscar en Presto' })).toBeInTheDocument()
    expect(screen.getByRole('combobox')).toHaveFocus()
  })

  it('filtra por lo que se escribe', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    await user.keyboard('{Control>}k{/Control}')
    await user.type(await screen.findByRole('combobox'), 'reportes')

    expect(screen.getByRole('option', { name: /Reportes/ })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /Inversiones/ })).not.toBeInTheDocument()
  })

  it('navega con Enter al resultado marcado', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    await user.keyboard('{Control>}k{/Control}')
    const input = await screen.findByRole('combobox')
    await user.type(input, 'presupuestos')
    await user.keyboard('{Enter}')

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Presupuestos' })).toBeInTheDocument()
    })
  })

  it('recorre los resultados con las flechas', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    await user.keyboard('{Control>}k{/Control}')
    const input = await screen.findByRole('combobox')

    expect(input).toHaveAttribute('aria-activedescendant', 'resultado-inicio')

    await user.keyboard('{ArrowDown}')
    expect(input).toHaveAttribute('aria-activedescendant', 'resultado-prestamos')

    await user.keyboard('{ArrowUp}')
    expect(input).toHaveAttribute('aria-activedescendant', 'resultado-inicio')
  })

  it('se cierra con Escape', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    await user.keyboard('{Control>}k{/Control}')
    await screen.findByRole('dialog', { name: 'Buscar en Presto' })

    await user.keyboard('{Escape}')

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Buscar en Presto' })).not.toBeInTheDocument()
    })
  })

  it('abre una acción de la pantalla actual', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    await user.keyboard('{Control>}k{/Control}')
    await user.type(await screen.findByRole('combobox'), 'transferir')
    await user.keyboard('{Enter}')

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: 'Transferir dinero' })).toBeInTheDocument()
    })
  })
})
