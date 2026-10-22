import { BrowserRouter } from 'react-router-dom'

import { AppProviders } from './app/providers'
import { AppRoutes } from './app/routes'
import { AuthProvider } from './features/auth/AuthProvider'

export default function App() {
  return (
    <AppProviders>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </AppProviders>
  )
}
