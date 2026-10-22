import { Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from '../components/layout/AppShell'
import { BudgetsPage } from '../features/budgets/BudgetsPage'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { LoginPage } from '../features/auth/LoginPage'
import { LoanDetailPage } from '../features/loans/LoanDetailPage'
import { LoansPage } from '../features/loans/LoansPage'
import { InvestmentsPage } from '../features/investments/InvestmentsPage'
import { MarketplacePage } from '../features/offers/MarketplacePage'
import { ProfilePage } from '../features/auth/ProfilePage'
import { RegisterPage } from '../features/auth/RegisterPage'
import { RedirectIfAuthenticated, RequireAuth } from '../features/auth/guards'
import { WalletsPage } from '../features/ledger/WalletsPage'
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
        <Route path="/panel" element={<DashboardPage />} />
        <Route path="/billetera" element={<WalletsPage />} />
        <Route path="/ofertas" element={<MarketplacePage />} />
        <Route path="/prestamos" element={<LoansPage />} />
        <Route path="/prestamos/:loanId" element={<LoanDetailPage />} />
        <Route path="/inversiones" element={<InvestmentsPage />} />
        <Route path="/presupuestos" element={<BudgetsPage />} />
        <Route path="/reportes" element={<PendingPage title="Reportes" />} />
        <Route path="/avisos" element={<PendingPage title="Avisos" />} />
        <Route path="/perfil" element={<ProfilePage />} />
      </Route>

      <Route path="*" element={<Navigate to="/panel" replace />} />
    </Routes>
  )
}
