import { QueryClientProvider } from '@tanstack/react-query'
import type { QueryClient } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { createQueryClient } from '../lib/query/client'

export interface AppProvidersProps {
  children: ReactNode
  queryClient?: QueryClient
}

/** Proveedores de la aplicación: consultas de TanStack Query. */
export function AppProviders({ children, queryClient }: AppProvidersProps) {
  const client = queryClient ?? createQueryClient()

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
