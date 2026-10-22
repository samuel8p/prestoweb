import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'

import { Icon } from '../../components/ui/Icon'
import type { IconName } from '../../components/ui/Icon'

export interface Shortcut {
  id: string
  label: string
  /** Valor destacado de la ficha. */
  value: ReactNode
  detail: string
  to: string
  icon: IconName
}

export interface ShortcutsProps {
  shortcuts: Shortcut[]
}

/**
 * Accesos compactos.
 *
 * Solo aparecen si hay datos: una próxima cuota, una inversión o un
 * presupuesto. Si no hay, no se muestra la ficha.
 */
export function Shortcuts({ shortcuts }: ShortcutsProps) {
  if (shortcuts.length === 0) {
    return null
  }

  return (
    <ul className="space-y-2">
      {shortcuts.map((shortcut) => (
        <li key={shortcut.id}>
          <Link
            to={shortcut.to}
            className="flex items-center gap-3 rounded-[var(--radius-control)] border border-line bg-surface px-4 py-3 transition-[transform,box-shadow] duration-200 ease-out hover:-translate-y-0.5 hover:shadow-card"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-tint text-primary">
              <Icon name={shortcut.icon} size={17} />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-[13px] font-semibold text-ink">{shortcut.label}</span>
              <span className="block truncate text-xs text-ink-muted">{shortcut.detail}</span>
            </span>
            <span className="shrink-0 text-[13px] font-bold text-ink tabular">
              {shortcut.value}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  )
}
