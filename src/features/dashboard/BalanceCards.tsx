import { useState } from 'react'

import { Badge } from '../../components/ui/Badge'
import { Icon } from '../../components/ui/Icon'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import type { Account } from '../../lib/api/types'
import type { Currency } from '../../lib/money/format'

const CURRENCY_LABEL: Record<Currency, string> = { ARS: 'Pesos', USD: 'Dólares' }

export interface BalanceCardsProps {
  accounts: Account[]
  currency: Currency
  onCurrencyChange: (currency: Currency) => void
  onCreateWallet: (currency: Currency) => void
}

/**
 * Saldos por moneda.
 *
 * La moneda activa vive en una tarjeta grande con pestañas; la otra queda
 * como tarjeta secundaria, desplazada y con otro radio. Nunca se suman.
 */
export function BalanceCards({
  accounts,
  currency,
  onCurrencyChange,
  onCreateWallet,
}: BalanceCardsProps) {
  const [hidden, setHidden] = useState(false)
  const active = accounts.find((account) => account.currency === currency)
  const other: Currency = currency === 'ARS' ? 'USD' : 'ARS'
  const otherAccount = accounts.find((account) => account.currency === other)

  return (
    <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
      {/* Tarjeta principal */}
      <section
        aria-label={`Saldo en ${CURRENCY_LABEL[currency]}`}
        className="on-dark relative overflow-hidden rounded-[1.25rem_1.25rem_1.25rem_0.5rem] bg-[linear-gradient(135deg,#06303A_0%,#0B4A57_100%)] p-5 pb-6 pt-12 shadow-raised sm:p-7 sm:pb-7 sm:pt-14"
      >
        <div aria-hidden="true" className="wave-pattern pointer-events-none absolute inset-0" />

        {/* Pestañas con muesca */}
        <div
          role="tablist"
          aria-label="Moneda del saldo"
          className="absolute left-5 top-0 flex items-end gap-1 sm:left-7"
        >
          {(['ARS', 'USD'] as Currency[]).map((option) => {
            const selected = option === currency

            return (
              <button
                key={option}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => onCurrencyChange(option)}
                className={`relative rounded-t-lg px-4 py-2 text-[11px] font-bold uppercase tracking-[0.1em] transition-colors duration-200 ${
                  selected ? 'bg-chrome-800 text-turquoise' : 'text-white/45 hover:text-white/80'
                }`}
              >
                {CURRENCY_LABEL[option]}
                {selected ? (
                  <span
                    aria-hidden="true"
                    className="absolute -bottom-[7px] left-0 h-3 w-3 -rotate-45 bg-chrome-800"
                  />
                ) : null}
              </button>
            )
          })}
        </div>

        <div className="relative flex items-start justify-between gap-4">
          <div>
            <p className="label-caps text-white/50">Saldo disponible</p>
            <p className="mt-3 text-[40px] font-bold leading-none tracking-tight text-white tabular sm:text-[48px]">
              {active ? (
                hidden ? (
                  '••••••'
                ) : (
                  <MoneyAmount
                    value={active.balance}
                    currency={currency}
                    className="[&>span]:text-inherit"
                  />
                )
              ) : (
                '—'
              )}
            </p>
            <p className="mt-2 text-[13px] text-white/50">
              {active ? `Billetera ${active.id.slice(0, 8)}…` : 'Sin billetera en esta moneda'}
            </p>
          </div>

          <button
            type="button"
            onClick={() => setHidden((value) => !value)}
            aria-label={hidden ? 'Mostrar los saldos' : 'Ocultar los saldos'}
            aria-pressed={hidden}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-control)] text-white/70 transition-colors duration-200 hover:bg-white/10 hover:text-white"
          >
            <Icon name={hidden ? 'eye' : 'eye'} size={18} />
          </button>
        </div>

        {!active ? (
          <div className="relative mt-5">
            <button
              type="button"
              onClick={() => onCreateWallet(currency)}
              className="rounded-[var(--radius-control)] bg-white/10 px-4 py-2 text-[13px] font-semibold text-white transition-colors duration-200 hover:bg-white/20"
            >
              Abrir billetera en {CURRENCY_LABEL[currency]}
            </button>
          </div>
        ) : null}
      </section>

      {/* Tarjeta secundaria */}
      <section
        aria-label={`Saldo en ${CURRENCY_LABEL[other]}`}
        className="flex flex-col justify-between rounded-[0.75rem_1.25rem_1.25rem_1.25rem] border border-line bg-surface p-5 shadow-card transition-[transform,box-shadow] duration-200 ease-out hover:-translate-y-0.5 hover:shadow-raised lg:-ml-6 lg:mt-8"
      >
        <div className="flex items-start justify-between gap-3">
          <p className="label-caps text-ink-subtle">{CURRENCY_LABEL[other]}</p>
          {otherAccount ? (
            <Badge tone="neutral">{other}</Badge>
          ) : (
            <Badge tone="warning" dot>
              Sin abrir
            </Badge>
          )}
        </div>

        <div className="mt-4">
          <p className="text-2xl font-bold leading-none tracking-tight text-ink tabular">
            {otherAccount ? (
              hidden ? (
                '••••••'
              ) : (
                <MoneyAmount
                  value={otherAccount.balance}
                  currency={other}
                  className="[&>span]:text-inherit"
                />
              )
            ) : (
              '—'
            )}
          </p>
          {otherAccount ? (
            <p className="mt-1.5 text-xs text-ink-muted tabular">
              Billetera {otherAccount.id.slice(0, 8)}…
            </p>
          ) : (
            <button
              type="button"
              onClick={() => onCreateWallet(other)}
              className="mt-1.5 text-[13px] font-semibold text-primary hover:underline"
            >
              Abrir billetera en {CURRENCY_LABEL[other]}
            </button>
          )}
        </div>
      </section>
    </div>
  )
}
