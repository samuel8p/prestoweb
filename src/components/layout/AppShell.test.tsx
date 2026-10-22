import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { AppRoutes } from '../../app/routes'
import { renderWithProviders } from '../../test/render'

describe('menú y rutas', () => {
  it('muestra las cinco secciones del escritorio', async () => {
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    const nav = screen.getByRole('navigation', { name: 'Principal' })
    for (const label of ['Inicio', 'Préstamos', 'Inversiones', 'Presupuestos', 'Reportes']) {
      expect(screen.getAllByRole('link', { name: label }).length).toBeGreaterThan(0)
    }
    expect(nav).toBeInTheDocument()
  })

  it('saca Billetera y Avisos del menú del escritorio', async () => {
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    const nav = screen.getByRole('navigation', { name: 'Principal' })
    expect(nav.textContent).not.toContain('Billetera')
    expect(nav.textContent).not.toContain('Avisos')
  })

  it('tiene una barra inferior de cinco destinos en el móvil', async () => {
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    expect(screen.getByRole('button', { name: 'Más' })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Presupuestos' }).length).toBeGreaterThan(0)
  })

  it('el menú "Más" del móvil lista Reportes, Avisos y Perfil', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'Más' }))

    expect((await screen.findAllByRole('link', { name: 'Reportes' })).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Avisos' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Perfil' })).toBeInTheDocument()
  })

  it('el avatar lleva a Perfil y a cerrar sesión', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'Mi cuenta' }))

    expect(await screen.findByRole('link', { name: 'Mi perfil' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cerrar sesión' })).toBeInTheDocument()
  })

  it('redirige /panel a Inicio', async () => {
    renderWithProviders(<AppRoutes />, { route: '/panel', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })
  })

  it('redirige /ofertas a la pestaña de ofertas de Préstamos', async () => {
    renderWithProviders(<AppRoutes />, { route: '/ofertas', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Préstamos' })).toBeInTheDocument()
    })
    expect(screen.getByRole('tab', { name: 'Ofertas' })).toHaveAttribute('aria-selected', 'true')
  })

  it('deja /billetera como el historial de movimientos', async () => {
    renderWithProviders(<AppRoutes />, { route: '/billetera', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Movimientos' })).toBeInTheDocument()
    })
  })
})
