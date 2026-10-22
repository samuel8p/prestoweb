import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { AppRoutes } from '../../app/routes'
import { renderWithProviders } from '../../test/render'
import { server } from '../../test/msw/server'

describe('LoginPage', () => {
  it('inicia sesión y entra al panel', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/ingresar', session: 'anonymous' })

    await user.type(screen.getByLabelText('Email'), 'ana@example.com')
    await user.type(screen.getByLabelText('Contraseña'), 'Presto1234')
    await user.click(screen.getByRole('button', { name: 'Ingresar' }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Panel' })).toBeInTheDocument()
    })
    expect(screen.queryByRole('button', { name: 'Ingresar' })).not.toBeInTheDocument()
  })

  it('muestra el error cuando las credenciales no son válidas', async () => {
    server.use(
      http.post('*/api/v1/auth/login/', () =>
        HttpResponse.json(
          { error: { code: 'not_authenticated', message: 'Email o contraseña incorrectos.' } },
          { status: 401 },
        ),
      ),
    )

    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/ingresar', session: 'anonymous' })

    await user.type(screen.getByLabelText('Email'), 'ana@example.com')
    await user.type(screen.getByLabelText('Contraseña'), 'mala')
    await user.click(screen.getByRole('button', { name: 'Ingresar' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Email o contraseña incorrectos.')
    })
  })

  it('valida el email antes de llamar a la API', async () => {
    const user = userEvent.setup()
    renderWithProviders(<AppRoutes />, { route: '/ingresar', session: 'anonymous' })

    await user.type(screen.getByLabelText('Email'), 'no-es-un-email')
    await user.type(screen.getByLabelText('Contraseña'), 'Presto1234')
    await user.click(screen.getByRole('button', { name: 'Ingresar' }))

    await waitFor(() => {
      expect(screen.getByText('Ingresá un email válido.')).toBeInTheDocument()
    })
  })
})
