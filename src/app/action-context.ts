import { createContext, useContext } from 'react'

export interface ActionRegistry {
  /** Registra lo que hace una acción (por ejemplo, abrir un modal). */
  register: (id: string, handler: () => void) => () => void
  /** Ejecuta una acción registrada. */
  run: (id: string) => boolean
}

export const ActionContext = createContext<ActionRegistry | null>(null)

/** Permite registrar y ejecutar acciones de la interfaz. */
export function useActions(): ActionRegistry {
  const context = useContext(ActionContext)
  if (!context) {
    throw new Error('useActions se tiene que usar dentro de <ActionProvider>.')
  }
  return context
}
