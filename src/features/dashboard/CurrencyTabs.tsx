import { useRef } from 'react'

export interface CurrencyTabsProps {
  value: 'ARS' | 'USD'
  onChange: (value: 'ARS' | 'USD') => void
}

const TABS: Array<{ id: 'ARS' | 'USD'; label: string }> = [
  { id: 'ARS', label: 'Pesos' },
  { id: 'USD', label: 'Dólares' },
]

/**
 * Pestañas de moneda.
 *
 * Comportamiento de tabs accesible: `role="tablist"` / `role="tab"`, la
 * seleccionada con `aria-selected` y las flechas izquierda/derecha mueven la
 * selección.
 */
export function CurrencyTabs({ value, onChange }: CurrencyTabsProps) {
  const refs = useRef<Array<HTMLButtonElement | null>>([])

  function move(step: number) {
    const current = TABS.findIndex((tab) => tab.id === value)
    const next = (current + step + TABS.length) % TABS.length
    const target = TABS[next]
    if (!target) {
      return
    }
    onChange(target.id)
    refs.current[next]?.focus()
  }

  return (
    <div role="tablist" aria-label="Moneda del saldo" className="flex gap-1">
      {TABS.map((tab, index) => {
        const selected = tab.id === value

        return (
          <button
            key={tab.id}
            ref={(element) => {
              refs.current[index] = element
            }}
            type="button"
            role="tab"
            id={`pestana-${tab.id}`}
            aria-selected={selected}
            aria-controls="panel-saldo"
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(tab.id)}
            onKeyDown={(event) => {
              if (event.key === 'ArrowRight') {
                event.preventDefault()
                move(1)
              }
              if (event.key === 'ArrowLeft') {
                event.preventDefault()
                move(-1)
              }
            }}
            className={`rounded-[var(--radius-control)] px-3 py-1.5 text-[13px] font-bold transition-colors duration-200 ${
              selected
                ? 'bg-primary text-white'
                : 'text-ink-muted hover:bg-surface-muted hover:text-ink'
            }`}
          >
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}
