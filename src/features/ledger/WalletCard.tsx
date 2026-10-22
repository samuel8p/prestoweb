import { Badge } from '../../components/ui/Badge'
import { Card } from '../../components/ui/Card'
import { Icon } from '../../components/ui/Icon'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import type { Account } from '../../lib/api/types'

export interface WalletCardProps {
  account: Account
  /** `true` si esta billetera es la que está en pantalla. */
  selected?: boolean
}

/**
 * Tarjeta de una billetera.
 *
 * Cada billetera es de una sola moneda: nunca se suman importes de ARS y USD.
 */
export function WalletCard({ account, selected = false }: WalletCardProps) {
  const currency = account.currency === 'USD' ? 'USD' : 'ARS'

  return (
    <Card
      className={`p-5 transition-colors ${selected ? 'border-brand-300 ring-1 ring-brand-100' : ''}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
            <Icon name="wallet" size={16} />
          </span>
          <div>
            <p className="text-[13px] font-medium text-slate-700">Billetera {currency}</p>
            <p className="text-[11px] text-slate-400 tabular">{account.id.slice(0, 8)}…</p>
          </div>
        </div>

        {selected ? (
          <Badge tone="info" dot>
            En pantalla
          </Badge>
        ) : (
          <Badge tone="neutral">
            {account.kind === 'user_wallet' ? 'Billetera' : account.kind}
          </Badge>
        )}
      </div>

      <p className="mt-4 text-2xl font-semibold tracking-tight text-slate-900 tabular">
        <MoneyAmount value={account.balance} currency={currency} />
      </p>
      <p className="mt-1 text-xs text-slate-500">Saldo disponible</p>
    </Card>
  )
}
