import type { IconName } from '../../components/ui/Icon'

export interface QuickAction {
  id: 'ingresar' | 'transferir' | 'billetera'
  label: string
  hint: string
  icon: IconName
  /** Forma propia de la ficha. */
  shape: string
}

/**
 * Las tres acciones de Inicio.
 *
 * Cada ficha tiene una forma distinta: son tres accesos y no un bloque
 * uniforme de botones.
 */
export const QUICK_ACTIONS: QuickAction[] = [
  {
    id: 'ingresar',
    label: 'Ingresar',
    hint: 'Sumar dinero a tu billetera',
    icon: 'arrowDownLeft',
    shape: 'rounded-2xl',
  },
  {
    id: 'transferir',
    label: 'Transferir',
    hint: 'Mandar dinero por alias',
    icon: 'swap',
    shape: 'rounded-[1.75rem]',
  },
  {
    id: 'billetera',
    label: 'Tu billetera',
    hint: 'Tu alias y tus identificadores',
    icon: 'wallet',
    shape: 'rounded-[1.25rem_0.375rem_1.25rem_1.25rem]',
  },
]
