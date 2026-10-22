import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ErrorBoundary } from '../components/ErrorBoundary'

function Boom(): never {
  throw new Error('Falla de prueba')
}

describe('ErrorBoundary', () => {
  it('muestra un mensaje y el error cuando una pantalla se rompe', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)

    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    )

    expect(screen.getByRole('heading', { name: 'Algo salió mal' })).toBeInTheDocument()
    expect(screen.getByText('Falla de prueba')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Recargar la página' })).toBeInTheDocument()

    consoleError.mockRestore()
  })

  it('deja reintentar sin recargar la página', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const user = userEvent.setup()

    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    )

    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(screen.getByRole('heading', { name: 'Algo salió mal' })).toBeInTheDocument()

    consoleError.mockRestore()
  })
})
