import { Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from '../components/layout/AppShell'
import { BudgetsPage } from '../features/budgets/BudgetsPage'
import { InicioPage } from '../features/dashboard/InicioPage'
import { LoginPage } from '../features/auth/LoginPage'
import { LoanDetailPage } from '../features/loans/LoanDetailPage'
import { PrestamosPage } from '../features/loans/PrestamosPage'
import { InvestmentsPage } from '../features/investments/InvestmentsPage'
import { MovimientosPage } from '../features/ledger/MovimientosPage'
import { ProfilePage } from '../features/auth/ProfilePage'
import { ReportsPage } from '../features/reports/ReportsPage'
import { NotificationsPage } from '../features/notifications/NotificationsPage'
import { RegisterPage } from '../features/auth/RegisterPage'
import { RedirectIfAuthenticated, RequireAuth } from '../features/auth/guards'

/**
 * Rutas de la aplicación.
 *
 * Las pantallas que se fusionaron (Inicio y Billetera, Ofertas y Préstamos)
 * redirigen a su nueva ubicación, así que los links viejos siguen funcionando.
 */
export function AppRoutes() {
  return (
    <Routes>
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
        <Route path="/" element={<InicioPage />} />

        {/* Rutas fusionadas: siguen funcionando y llevan a su nueva pantalla */}
        <Route path="/panel" element={<Navigate to="/" replace />} />
        <Route path="/billetera" element={<MovimientosPage />} />
        <Route path="/ofertas" element={<Navigate to="/prestamos?vista=ofertas" replace />} />

        <Route path="/prestamos" element={<PrestamosPage />} />
        <Route path="/prestamos/:loanId" element={<LoanDetailPage />} />
        <Route path="/inversiones" element={<InvestmentsPage />} />
        <Route path="/presupuestos" element={<BudgetsPage />} />
        <Route path="/reportes" element={<ReportsPage />} />
        <Route path="/avisos" element={<NotificationsPage />} />
        <Route path="/perfil" element={<ProfilePage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
