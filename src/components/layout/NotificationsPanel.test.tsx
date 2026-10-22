import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { AppRoutes } from '../../app/routes'
import { renderWithProviders } from '../../test/render'

describe('panel de avisos', () => {
  it('abre con la campana y lista los avisos recientes', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'Avisos' }))

    expect(await screen.findByText('Cuota por vencer')).toBeInTheDocument()
  })

  it('ofrece "Ver todos" y "Configurar"', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'Avisos' }))

    const links = await screen.findAllByRole('link', { name: 'Ver todos' })
    expect(links.some((link) => link.getAttribute('href') === '/avisos')).toBe(true)
    expect(screen.getByRole('link', { name: 'Configurar' })).toHaveAttribute(
      'href',
      '/avisos#preferencias',
    )
  })

  it('no muestra insignia con contador: el esquema no trae estado de lectura', async () => {
    renderWithProviders(<AppRoutes />, { route: '/', session: 'authenticated' })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Hola, Ana' })).toBeInTheDocument()
    })

    const bell = screen.getByRole('button', { name: 'Avisos' })
    expect(bell.textContent).toBe('')
    expect(bell.querySelector('[data-badge]')).toBeNull()
  })
})
