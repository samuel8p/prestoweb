import { useState } from 'react'

import { Icon } from '../../components/ui/Icon'
import { MoneyAmount } from '../../components/ui/MoneyAmount'
import type { Account } from '../../lib/api/types'
import type { Currency } from '../../lib/money/format'
import { CurrencyTabs } from './CurrencyTabs'
import { QuickActions } from './QuickActions'

export interface BalanceSurfaceProps {
  accounts: Account[]
  currency: Currency
  onCurrencyChange: (currency: Currency) => void
  /** Saludo de la pantalla. */
  greeting: string
  /** Botón del buscador. */
  onSearch: () => void
  /** Botón de los avisos. */
  onNotifications: () => void
  /** Panel de avisos, que se ancla al botón de la campana. */
  notificationsPanel?: React.ReactNode
  /** Abre el movimiento de depósito en la moneda elegida. */
  onDeposit: (currency: Currency) => void
  /** Abre el movimiento de transferencia. */
  onTransfer: () => void
  /** Abre el panel con la billetera y el alias. */
  onWallet: () => void
  /** Abre el formulario para abrir una billetera en una moneda. */
  onCreateWallet: (currency: Currency) => void
}

/**
 * Superficie en L de Inicio.
 *
 * Arriba a la izquierda, el saludo y las pestañas de moneda; a la derecha, la
 * lupa y la campana. Abajo, a todo el ancho, el saldo y las acciones.
 */
export function BalanceSurface({
  accounts,
  currency,
  onCurrencyChange,
  greeting,
  onSearch,
  onNotifications,
  notificationsPanel,
  onDeposit,
  onTransfer,
  onWallet,
  onCreateWallet,
}: BalanceSurfaceProps) {
  const [hidden, setHidden] = useState(false)
  const account = accounts.find((item) => item.currency === currency)
  const other: Currency = currency === 'ARS' ? 'USD' : 'ARS'
  const otherAccount = accounts.find((item) => item.currency === other)

  return (
    <section
      aria-label="Saldo y accesos"
      className="on-dark relative overflow-hidden rounded-[24px] bg-[linear-gradient(135deg,#023E8A_0%,#0077B6_100%)] shadow-raised"
    >
      <div aria-hidden="true" className="wave-pattern pointer-events-none absolute inset-0" />

      {/* Brazo vertical de la L: saludo, pestañas y los iconos */}
      <div className="relative flex flex-wrap items-start justify-between gap-3 px-4 pt-4 sm:px-6 sm:pt-6">
        <div className="esquina-concava min-w-0 flex-1 rounded-[24px] bg-canvas px-4 pb-6 pt-4 sm:px-7 sm:pb-7 sm:pt-5">
          <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">{greeting}</h1>
          <div className="mt-3">
            <CurrencyTabs value={currency} onChange={onCurrencyChange} />
          </div>
        </div>

        <div className="relative flex items-center gap-1.5">
          <button
            type="button"
            onClick={onSearch}
            aria-label="Buscar"
            aria-haspopup="dialog"
            className="flex h-10 w-10 items-center justify-center rounded-full text-white/85 transition-colors duration-200 hover:bg-white/15 hover:text-white"
          >
            <Icon name="search" size={19} />
          </button>

          <button
            type="button"
            onClick={onNotifications}
            aria-label="Avisos"
            aria-expanded={Boolean(notificationsPanel)}
            className="flex h-10 w-10 items-center justify-center rounded-full text-white/85 transition-colors duration-200 hover:bg-white/15 hover:text-white"
          >
            <Icon name="bell" size={19} />
          </button>

          {notificationsPanel}
        </div>
      </div>

      {/* Brazo horizontal de la L: el saldo y las acciones */}
      <div
        id="panel-saldo"
        role="tabpanel"
        aria-labelledby={`pestana-${currency}`}
        className="relative px-4 pb-5 pt-5 sm:px-6 sm:pb-7"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="label-caps text-white/65">Saldo disponible</p>
            <p className="mt-2 text-[40px] font-bold leading-none tracking-tight text-white tabular sm:text-[48px]">
              {account ? (
                hidden ? (
                  '••••••'
                ) : (
                  <MoneyAmount
                    value={account.balance}
                    currency={currency}
                    className="[&>span]:text-inherit"
                  />
                )
              ) : (
                '—'
              )}
            </p>
            <p className="mt-2 text-[13px] text-white/60">
              {account
                ? `Billetera ${account.id.slice(0, 8)}…`
                : `Todavía no tenés una billetera en ${currency === 'ARS' ? 'pesos' : 'dólares'}`}
            </p>
          </div>

          <button
            type="button"
            onClick={() => setHidden((value) => !value)}
            aria-label={hidden ? 'Mostrar el saldo' : 'Ocultar el saldo'}
            aria-pressed={hidden}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-white/85 transition-colors duration-200 hover:bg-white/15 hover:text-white"
          >
            <Icon name="eye" size={19} />
          </button>
        </div>

        {/* Accesos */}
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <QuickActions
            currency={currency}
            onDeposit={onDeposit}
            onTransfer={onTransfer}
            onWallet={onWallet}
          />

          {!account ? (
            <button
              type="button"
              onClick={() => onCreateWallet(currency)}
              className="rounded-full bg-white/15 px-4 py-2.5 text-[13px] font-bold text-white transition-colors duration-200 hover:bg-white/25"
            >
              Abrir billetera en {currency === 'ARS' ? 'pesos' : 'dólares'}
            </button>
          ) : null}

          {otherAccount ? null : (
            <button
              type="button"
              onClick={() => onCreateWallet(other)}
              className="rounded-full bg-transparent px-4 py-2.5 text-[13px] font-semibold text-white/80 underline decoration-white/40 underline-offset-4 transition-colors duration-200 hover:text-white"
            >
              Abrir billetera en {other === 'ARS' ? 'pesos' : 'dólares'}
            </button>
          )}
        </div>
      </div>
    </section>
  )
}
