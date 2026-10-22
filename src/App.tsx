import { BrowserRouter } from 'react-router-dom'

import { AppProviders } from './app/providers'
import { AppRoutes } from './app/routes'
import { ErrorBoundary } from './components/ErrorBoundary'
import { AuthProvider } from './features/auth/AuthProvider'

export default function App() {
  return (
    <AppProviders>
      <AuthProvider>
        <ErrorBoundary>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </ErrorBoundary>
      </AuthProvider>
    </AppProviders>
  )
}
