import { Icon } from '../../components/ui/Icon'
import { QUICK_ACTIONS } from './quickActionsData'
import type { Currency } from '../../lib/money/format'

export interface QuickActionsProps {
  currency: Currency
  /** Abre el movimiento de depósito en la moneda elegida. */
  onDeposit: (currency: Currency) => void
  /** Abre el movimiento de transferencia. */
  onTransfer: () => void
  /** Abre el panel con la billetera y el alias. */
  onWallet: () => void
}

/** Las tres fichas de acceso: Ingresar, Transferir y Tu billetera. */
export function QuickActions({ currency, onDeposit, onTransfer, onWallet }: QuickActionsProps) {
  function handleClick(id: 'ingresar' | 'transferir' | 'billetera') {
    if (id === 'ingresar') {
      onDeposit(currency)
      return
    }
    if (id === 'transferir') {
      onTransfer()
      return
    }
    onWallet()
  }

  return (
    <ul className="flex flex-wrap gap-3">
      {QUICK_ACTIONS.map((action) => (
        <li key={action.id}>
          <button
            type="button"
            onClick={() => handleClick(action.id)}
            className={`flex items-center gap-2.5 bg-white/15 px-4 py-2.5 text-left text-white transition-[transform,background-color] duration-200 ease-out hover:bg-white/25 active:scale-[0.98] ${action.shape}`}
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/15 text-turquoise">
              <Icon name={action.icon} size={16} />
            </span>
            <span className="min-w-0">
              <span className="block text-[13px] font-bold leading-tight">{action.label}</span>
              <span className="block truncate text-[11px] leading-tight text-white/70">
                {action.hint}
              </span>
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}
