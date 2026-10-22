import { useId } from 'react'
import type { InputHTMLAttributes, ReactNode } from 'react'

import { Icon } from './Icon'
import type { IconName } from './Icon'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
  hint?: ReactNode
  /** Ícono a la izquierda del campo. */
  icon?: IconName
  /** Oculta la etiqueta visualmente (sigue estando para lectores de pantalla). */
  hideLabel?: boolean
}

const CONTROL =
  'w-full rounded-[var(--radius-control)] border bg-white px-3 py-2 text-sm text-ink shadow-xs transition-colors placeholder:text-ink-subtle focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-ink-muted'

/** Campo de texto con etiqueta, ayuda y error accesibles. */
export function Input({
  label,
  error,
  hint,
  icon,
  hideLabel = false,
  id,
  className = '',
  ...rest
}: InputProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const errorId = `${inputId}-error`
  const hintId = `${inputId}-hint`

  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={inputId}
        className={hideLabel ? 'sr-only' : 'text-[13px] font-medium text-ink'}
      >
        {label}
      </label>

      <div className="relative">
        {icon ? (
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-subtle">
            <Icon name={icon} size={16} />
          </span>
        ) : null}

        <input
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : hint ? hintId : undefined}
          className={`${CONTROL} ${
            error
              ? 'border-danger focus:border-danger focus:ring-danger-bg'
              : 'border-line-strong focus:border-primary focus:ring-primary/20'
          } ${icon ? 'pl-9' : ''} ${className}`}
          {...rest}
        />
      </div>

      {hint && !error ? (
        <p id={hintId} className="text-xs text-ink-muted">
          {hint}
        </p>
      ) : null}

      {error ? (
        <p id={errorId} role="alert" className="text-xs font-medium text-danger">
          {error}
        </p>
      ) : null}
    </div>
  )
}
