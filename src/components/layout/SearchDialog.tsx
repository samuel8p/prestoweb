import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'

import { Icon } from '../ui/Icon'
import { useActions } from '../../app/action-context'
import { SEARCH_ENTRIES } from '../../app/navigation'
import type { SearchEntry } from '../../app/navigation'

export interface SearchDialogProps {
  open: boolean
  onClose: () => void
}

/**
 * Buscador global.
 *
 * Solo del cliente: filtra un índice de secciones y acciones de la app. No
 * llama a la API. El foco queda atrapado en el campo (patrón de combobox) y se
 * navega con las flechas.
 */
export function SearchDialog({ open, onClose }: SearchDialogProps) {
  const navigate = useNavigate()
  const { run } = useActions()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)

  const results = useMemo(() => {
    const term = query.trim().toLowerCase()
    if (!term) {
      return SEARCH_ENTRIES
    }
    return SEARCH_ENTRIES.filter((entry) =>
      `${entry.label} ${entry.hint}`.toLowerCase().includes(term),
    )
  }, [query])

  // Al abrir se reinicia el buscador (patrón de "ajustar el estado cuando
  // cambia una prop", sin setState dentro de un efecto).
  const [wasOpen, setWasOpen] = useState(open)
  if (open !== wasOpen) {
    setWasOpen(open)
    if (open) {
      setQuery('')
      setActiveIndex(0)
    }
  }

  // Al escribir, el resultado activo vuelve al primero.
  const [lastQuery, setLastQuery] = useState(query)
  if (query !== lastQuery) {
    setLastQuery(query)
    setActiveIndex(0)
  }

  useEffect(() => {
    if (!open) {
      return undefined
    }
    inputRef.current?.focus()

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  if (!open) {
    return null
  }

  function activate(entry: SearchEntry) {
    if (entry.action) {
      run(entry.action)
      onClose()
      return
    }
    if (entry.to) {
      navigate(entry.to)
      onClose()
    }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex((index) => (results.length === 0 ? 0 : (index + 1) % results.length))
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((index) =>
        results.length === 0 ? 0 : (index - 1 + results.length) % results.length,
      )
      return
    }
    if (event.key === 'Enter') {
      event.preventDefault()
      const entry = results[activeIndex]
      if (entry) {
        activate(entry)
      }
    }
  }

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-[12vh]">
      <button
        type="button"
        aria-label="Cerrar el buscador"
        onClick={onClose}
        className="absolute inset-0 cursor-default bg-ocean/50 backdrop-blur-[2px] animate-fade-in"
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-label="Buscar en Presto"
        className="relative w-full max-w-xl overflow-hidden rounded-[var(--radius-card)] border border-line bg-surface shadow-raised animate-scale-in"
      >
        <div className="flex items-center gap-3 border-b border-line px-4">
          <Icon name="search" size={18} className="text-ink-subtle" />
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded="true"
            aria-controls="resultados-busqueda"
            aria-activedescendant={
              results[activeIndex] ? `resultado-${results[activeIndex]!.id}` : undefined
            }
            aria-label="Buscar secciones y acciones"
            placeholder="Buscar secciones y acciones…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleKeyDown}
            className="h-14 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-ink-subtle"
          />
          <kbd className="hidden rounded border border-line bg-surface-muted px-1.5 py-0.5 text-[10px] font-semibold text-ink-subtle sm:block">
            ESC
          </kbd>
        </div>

        <ul id="resultados-busqueda" role="listbox" className="max-h-[22rem] overflow-y-auto p-2">
          {results.length === 0 ? (
            <li className="px-3 py-6 text-center text-[13px] text-ink-muted">
              No encontramos nada para “{query}”.
            </li>
          ) : null}

          {results.map((entry, index) => {
            const active = index === activeIndex
            const previousGroup = index === 0 ? null : results[index - 1]?.group

            return (
              <li key={entry.id}>
                {entry.group !== previousGroup ? (
                  <p className="label-caps px-3 pb-1 pt-3 text-ink-subtle">{entry.group}</p>
                ) : null}

                <button
                  id={`resultado-${entry.id}`}
                  type="button"
                  role="option"
                  aria-selected={active}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => activate(entry)}
                  className={`flex w-full items-center gap-3 rounded-[var(--radius-control)] px-3 py-2.5 text-left transition-colors duration-150 ${
                    active ? 'bg-teal-tint' : 'hover:bg-surface-muted'
                  }`}
                >
                  <span
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                      active ? 'bg-teal text-white' : 'bg-surface-muted text-ink-muted'
                    }`}
                  >
                    <Icon name={entry.icon} size={16} />
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold text-ink">
                      {entry.label}
                    </span>
                    <span className="block truncate text-xs text-ink-muted">{entry.hint}</span>
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      </div>
    </div>,
    document.body,
  )
}
