import type { IconName } from '../../components/ui/Icon'

export interface QuickAction {
  id: string
  label: string
  hint: string
  icon: IconName
  /** Forma propia de la ficha. */
  shape: string
  tone: string
}

export const QUICK_ACTIONS: QuickAction[] = [
  {
    id: 'ingresar',
    label: 'Ingresar',
    hint: 'Sumar dinero a tu billetera',
    icon: 'arrowDownLeft',
    shape: 'rounded-2xl',
    tone: 'bg-teal-tint text-teal',
  },
  {
    id: 'transferir',
    label: 'Transferir',
    hint: 'Mandar dinero a otra billetera',
    icon: 'swap',
    shape: 'rounded-[1.75rem]',
    tone: 'bg-ocean-800 text-turquoise',
  },
  {
    id: 'retirar',
    label: 'Retirar',
    hint: 'Sacar dinero de tu billetera',
    icon: 'arrowUpRight',
    shape: 'rounded-[1.25rem_1.25rem_1.25rem_0.375rem]',
    tone: 'bg-warning-bg text-warning',
  },
  {
    id: 'billetera',
    label: 'Tu billetera',
    hint: 'Identificador para recibir transferencias',
    icon: 'wallet',
    shape: 'rounded-[1.25rem_0.375rem_1.25rem_1.25rem]',
    tone: 'bg-surface-muted text-ink',
  },
]
