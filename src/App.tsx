import { BrowserRouter } from 'react-router-dom'

import { AppProviders } from './app/providers'
import { AppRoutes } from './app/routes'
import { ActionProvider } from './app/actions'
import { ErrorBoundary } from './components/ErrorBoundary'
import { AuthProvider } from './features/auth/AuthProvider'

export default function App() {
  return (
    <AppProviders>
      <AuthProvider>
        <ActionProvider>
          <ErrorBoundary>
            <BrowserRouter>
              <AppRoutes />
            </BrowserRouter>
          </ErrorBoundary>
        </ActionProvider>
      </AuthProvider>
    </AppProviders>
  )
}
