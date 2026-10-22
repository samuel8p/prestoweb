import { useCallback, useMemo, useRef } from 'react'
import type { ReactNode } from 'react'

import { ActionContext } from './action-context'
import type { ActionRegistry } from './action-context'

export interface ActionProviderProps {
  children: ReactNode
}

/**
 * Bus de acciones de la interfaz.
 *
 * Permite que el buscador global (que vive en el encabezado) abra los modales
 * de la pantalla actual sin know-how de sus estados: cada pantalla registra
 * lo que hace y el buscador solo la ejecuta por id.
 */
export function ActionProvider({ children }: ActionProviderProps) {
  const handlers = useRef(new Map<string, () => void>())

  const register = useCallback((id: string, handler: () => void) => {
    handlers.current.set(id, handler)
    return () => {
      handlers.current.delete(id)
    }
  }, [])

  const run = useCallback((id: string) => {
    const handler = handlers.current.get(id)
    if (!handler) {
      return false
    }
    handler()
    return true
  }, [])

  const value = useMemo<ActionRegistry>(() => ({ register, run }), [register, run])

  return <ActionContext.Provider value={value}>{children}</ActionContext.Provider>
}
