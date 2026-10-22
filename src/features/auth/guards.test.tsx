import { screen, waitFor } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { renderWithProviders } from '../../test/render'
import { RequireAuth } from './guards'

function ProtectedArea() {
  return <p>Zona protegida</p>
}

describe('RequireAuth', () => {
  it('manda al login cuando no hay sesión', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/ingresar" element={<p>Pantalla de login</p>} />
        <Route
          path="/panel"
          element={
            <RequireAuth>
              <ProtectedArea />
            </RequireAuth>
          }
        />
      </Routes>,
      { route: '/panel', session: 'anonymous' },
    )

    await waitFor(() => {
      expect(screen.getByText('Pantalla de login')).toBeInTheDocument()
    })
    expect(screen.queryByText('Zona protegida')).not.toBeInTheDocument()
  })

  it('deja pasar a la zona protegida cuando hay sesión', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/ingresar" element={<p>Pantalla de login</p>} />
        <Route
          path="/panel"
          element={
            <RequireAuth>
              <ProtectedArea />
            </RequireAuth>
          }
        />
      </Routes>,
      { route: '/panel', session: 'authenticated' },
    )

    await waitFor(() => {
      expect(screen.getByText('Zona protegida')).toBeInTheDocument()
    })
  })
})
