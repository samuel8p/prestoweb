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
      className={`p-5 transition-[transform,box-shadow,border-color] duration-200 ease-out hover:-translate-y-0.5 hover:shadow-raised ${
        selected ? 'border-teal/40 ring-1 ring-teal/20' : ''
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-[0.6rem] bg-teal-tint text-teal">
            <Icon name="wallet" size={17} />
          </span>
          <div>
            <p className="text-[13px] font-semibold text-ink">Billetera {currency}</p>
            <p className="text-[11px] text-ink-subtle tabular">{account.id.slice(0, 8)}…</p>
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

      <p className="mt-4 text-[32px] font-bold leading-none tracking-tight text-ink tabular">
        <MoneyAmount value={account.balance} currency={currency} />
      </p>
      <p className="mt-1.5 label-caps text-ink-subtle">Saldo disponible</p>
    </Card>
  )
}
