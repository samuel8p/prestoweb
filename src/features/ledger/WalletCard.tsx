import { Card } from '../../components/ui/Card'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import type { Account } from '../../lib/api/types'

export interface WalletCardProps {
  account: Account
}

/**
 * Tarjeta de una billetera.
 *
 * Cada billetera es de una sola moneda: nunca se suman importes de ARS y USD.
 */
export function WalletCard({ account }: WalletCardProps) {
  const currency = account.currency === 'USD' ? 'USD' : 'ARS'

  return (
    <Card className="p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{currency}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
        <MoneyAmount value={account.balance} currency={currency} />
      </p>
      <p className="mt-1 truncate text-xs text-slate-400">ID: {account.id}</p>
    </Card>
  )
}
