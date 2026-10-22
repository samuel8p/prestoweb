import { Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from '../components/layout/AppShell'
import { LoginPage } from '../features/auth/LoginPage'
import { ProfilePage } from '../features/auth/ProfilePage'
import { RegisterPage } from '../features/auth/RegisterPage'
import { RedirectIfAuthenticated, RequireAuth } from '../features/auth/guards'
import { PendingPage } from './PendingPage'

/** Rutas de la aplicación. */
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/panel" replace />} />

      <Route
        path="/ingresar"
        element={
          <RedirectIfAuthenticated>
            <LoginPage />
          </RedirectIfAuthenticated>
        }
      />

      <Route
        path="/registro"
        element={
          <RedirectIfAuthenticated>
            <RegisterPage />
          </RedirectIfAuthenticated>
        }
      />

      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route path="/panel" element={<PendingPage title="Panel" />} />
        <Route path="/billetera" element={<PendingPage title="Billetera" />} />
        <Route path="/ofertas" element={<PendingPage title="Ofertas" />} />
        <Route path="/prestamos" element={<PendingPage title="Préstamos" />} />
        <Route path="/inversiones" element={<PendingPage title="Inversiones" />} />
        <Route path="/presupuestos" element={<PendingPage title="Presupuestos" />} />
        <Route path="/reportes" element={<PendingPage title="Reportes" />} />
        <Route path="/avisos" element={<PendingPage title="Avisos" />} />
        <Route path="/perfil" element={<ProfilePage />} />
      </Route>

      <Route path="*" element={<Navigate to="/panel" replace />} />
    </Routes>
  )
}
