import { useSearchParams } from 'react-router-dom'
import type { ReactNode } from 'react'

export interface SectionTabsProps {
  /** Identificador de la pestaña activa. */
  value: string
  tabs: Array<{ id: string; label: string; content: ReactNode }>
  /** Prefijo del query param que guarda la pestaña activa. */
  param?: string
}

/**
 * Pestañas de una sección.
 *
 * La pestaña activa vive en el query param: la URL es compartible y el
 * "volver" del navegador funciona.
 */
export function SectionTabs({ value, tabs, param = 'vista' }: SectionTabsProps) {
  const [searchParams, setSearchParams] = useSearchParams()

  function select(id: string) {
    const next = new URLSearchParams(searchParams)
    next.set(param, id)
    setSearchParams(next, { replace: false })
  }

  const active = tabs.find((tab) => tab.id === value) ?? tabs[0]

  return (
    <div className="flex flex-col gap-6">
      <div
        role="tablist"
        aria-label="Secciones"
        className="flex flex-wrap gap-1 border-b border-line"
      >
        {tabs.map((tab) => {
          const selected = tab.id === active?.id

          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={selected}
              onClick={() => select(tab.id)}
              className={`-mb-px border-b-2 px-3 py-2 text-[13px] font-semibold transition-colors duration-200 ${
                selected
                  ? 'border-teal text-teal'
                  : 'border-transparent text-ink-muted hover:text-ink'
              }`}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      <div role="tabpanel">{active?.content}</div>
    </div>
  )
}
