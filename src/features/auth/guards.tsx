import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'

import { Spinner } from '../../components/ui/Spinner'
import { useAuth } from './auth-context'

/** Pantalla de espera mientras se recupera la sesión. */
export function AuthLoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <Spinner label="Cargando tu sesión" />
    </div>
  )
}

/** Ruta protegida: sin sesión, va al login. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return <AuthLoadingScreen />
  }

  if (status === 'anonymous') {
    return <Navigate to="/ingresar" replace state={{ from: location.pathname }} />
  }

  return <>{children}</>
}

/** Ruta de guests: con sesión, va al panel. */
export function RedirectIfAuthenticated({ children }: { children: ReactNode }) {
  const { status } = useAuth()

  if (status === 'loading') {
    return <AuthLoadingScreen />
  }

  if (status === 'authenticated') {
    return <Navigate to="/panel" replace />
  }

  return <>{children}</>
}
