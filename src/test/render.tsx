import type { ReactElement, ReactNode } from 'react'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { AppProviders } from '../app/providers'
import { ActionProvider } from '../app/actions'
import { AuthProvider } from '../features/auth/AuthProvider'
import { createQueryClient } from '../lib/query/client'

export interface RenderOptions {
  /** Ruta inicial del router de memoria. */
  route?: string
  /** Con `authenticated` se simula una sesión ya iniciada. */
  session?: 'anonymous' | 'authenticated'
}

export interface RenderResult {
  queryClient: ReturnType<typeof createQueryClient>
}

/**
 * Renderiza un componente con los proveedores de la app.
 *
 * @param ui - el componente a renderizar.
 * @param options - ruta inicial y estado de la sesión.
 */
export function renderWithProviders(ui: ReactElement, options: RenderOptions = {}): RenderResult {
  const queryClient = createQueryClient()

  window.sessionStorage.clear()
  if (options.session === 'authenticated') {
    window.sessionStorage.setItem('presto.refresh_token', 'refresh-token')
  }

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <AppProviders queryClient={queryClient}>
        <AuthProvider>
          <ActionProvider>
            <MemoryRouter initialEntries={[options.route ?? '/']}>{children}</MemoryRouter>
          </ActionProvider>
        </AuthProvider>
      </AppProviders>
    )
  }

  return { ...render(ui, { wrapper: Wrapper }), queryClient }
}
