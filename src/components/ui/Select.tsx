import { useId } from 'react'
import type { ReactNode, SelectHTMLAttributes } from 'react'

import { Icon } from './Icon'
import type { IconName } from './Icon'

export interface SelectOption {
  value: string
  label: string
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string
  options: SelectOption[]
  error?: string
  hint?: ReactNode
  icon?: IconName
  hideLabel?: boolean
}

/** Selector con etiqueta y error accesibles. */
export function Select({
  label,
  options,
  error,
  hint,
  icon,
  hideLabel = false,
  id,
  className = '',
  ...rest
}: SelectProps) {
  const generatedId = useId()
  const selectId = id ?? generatedId
  const errorId = `${selectId}-error`
  const hintId = `${selectId}-hint`

  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={selectId}
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

        <select
          id={selectId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : hint ? hintId : undefined}
          className={`w-full appearance-none rounded-[var(--radius-control)] border bg-white py-2 pl-3 pr-9 text-sm text-ink shadow-xs transition-colors focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-ink-muted ${
            error
              ? 'border-danger focus:border-danger focus:ring-danger-bg'
              : 'border-line-strong focus:border-primary focus:ring-primary/20'
          } ${icon ? 'pl-9' : ''} ${className}`}
          {...rest}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-subtle">
          <Icon name="chevronDown" size={15} />
        </span>
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
